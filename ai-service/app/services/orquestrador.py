"""Orquestrador de disparo de campanha.

Roda em background: percorre os contatos do público da campanha, gera/monta a
mensagem (IA ou manual), envia pela UAzAPI, grava o disparo e atualiza os
contadores — respeitando o intervalo configurado entre os envios.
"""

import asyncio
import json
import logging
import re

from app.db.redis import get_redis
from app.graph.build import gerar_mensagem
from app.services import repo
from app.services.uazapi import enviar_texto

logger = logging.getLogger("uvicorn.error")

# Mantém referência das tasks em andamento (evita coleta pelo GC).
_tasks: set[asyncio.Task] = set()


def thread_id_de(telefone: str, usuario_id: str, instancia_id: str) -> str:
    """Chave de memória/conversa: telefone_empresa_instancia."""
    return f"{telefone}_{usuario_id}_{instancia_id}"


def _formatar_telefone(t: str) -> str:
    nums = re.sub(r"\D", "", t or "")
    if nums.startswith("55") and len(nums) >= 12:
        return nums
    if len(nums) in (10, 11):
        return "55" + nums
    return nums


def _interpolar(template: str, contato: dict) -> str:
    return (
        (template or "")
        .replace("{nome}", contato.get("nome") or "")
        .replace("{telefone}", contato.get("telefone") or "")
        .replace("{empresa}", contato.get("empresa") or "")
        .replace("{observacao}", contato.get("observacao") or "")
        .replace("{etapa}", contato.get("etapa") or "")
    )


def agendar_disparo(app, campanha_id: str) -> None:
    """Dispara a campanha em background (não bloqueia a resposta HTTP)."""
    task = asyncio.create_task(_disparar(app, campanha_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _disparar(app, campanha_id: str) -> None:
    try:
        campanha = await repo.get_campanha(campanha_id)
        if not campanha:
            logger.error("[disparo] campanha %s não encontrada", campanha_id)
            return
        if not campanha.get("canal_id"):
            logger.error("[disparo] campanha %s sem canal vinculado", campanha_id)
            return

        # Claim atômico: evita disparo duplicado (clique duplo / múltiplos workers).
        if not await repo.claim_campanha(campanha_id):
            logger.warning("[disparo] campanha %s já reivindicada — ignorando", campanha_id)
            return

        instancia = await repo.get_instancia(campanha["canal_id"])
        if not instancia or not instancia.get("uazapi_token"):
            logger.error("[disparo] instância/token indisponível para campanha %s", campanha_id)
            await repo.atualizar_status_campanha(campanha_id, "falhou")
            return

        contatos = await repo.get_contatos_do_publico(campanha["publico_id"])
        if not contatos:
            logger.warning("[disparo] público sem contatos (campanha %s)", campanha_id)
            await repo.atualizar_status_campanha(campanha_id, "concluida")
            return

        # Ao retomar uma campanha pausada, não reenvia para quem já recebeu.
        ja_enviados = await repo.get_contatos_ja_enviados(campanha_id)

        modo = campanha.get("modo_mensagem") or "manual"
        intervalo = max(1, int(campanha.get("intervalo_segundos") or 10))
        usuario_id = campanha["usuario_id"]
        token = instancia["uazapi_token"]
        graph = app.state.graph
        redis = get_redis()

        logger.info(
            "[disparo] iniciando campanha %s (%d contatos, modo=%s, intervalo=%ds)",
            campanha_id, len(contatos), modo, intervalo,
        )

        enviados = 0
        falhas = 0
        pausado = False
        for i, contato in enumerate(contatos):
            # Pausa: se o status virou 'pausada' (pelo painel), interrompe sem concluir.
            if await repo.get_campanha_status(campanha_id) == "pausada":
                pausado = True
                logger.info("[disparo] campanha %s pausada — interrompendo", campanha_id)
                break

            # Retomada: pula contatos que já receberam.
            if str(contato["id"]) in ja_enviados:
                continue

            telefone = _formatar_telefone(contato.get("telefone") or "")
            if not telefone or len(telefone) < 10:
                await repo.inserir_disparo(
                    campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                    status="falhou", mensagem_enviada=None, erro="Telefone inválido",
                )
                await repo.incrementar_contadores(campanha_id, falhas=1)
                falhas += 1
                continue

            tid = thread_id_de(telefone, usuario_id, instancia["id"])

            try:
                if modo == "ia":
                    mensagem = await gerar_mensagem(
                        graph, thread_id=tid,
                        nome=contato.get("nome") or "",
                        observacao=contato.get("observacao") or "",
                    )
                else:
                    mensagem = _interpolar(campanha.get("mensagem") or "", contato)

                resultado = await enviar_texto(token=token, numero=telefone, texto=mensagem)
                ok = bool(resultado["sucesso"])
                await repo.inserir_disparo(
                    campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                    status="enviado" if ok else "falhou",
                    mensagem_enviada=mensagem,
                    erro=None if ok else f"UAzAPI HTTP {resultado['status_code']}",
                )
                if ok:
                    enviados += 1
                    await repo.incrementar_contadores(campanha_id, enviados=1)
                    # Salva o contexto no Redis para o webhook resolver a resposta depois.
                    await redis.set(
                        f"conv:{tid}",
                        json.dumps({
                            "campanha_id": str(campanha_id),
                            "contato_id": str(contato["id"]),
                            "usuario_id": str(usuario_id),
                            "instancia_id": str(instancia["id"]),
                            "telefone": telefone,
                        }),
                        ex=60 * 60 * 24 * 30,  # 30 dias
                    )
                else:
                    await repo.incrementar_contadores(campanha_id, falhas=1)
                    falhas += 1
            except Exception as e:  # noqa: BLE001 — não deixar 1 contato derrubar o lote
                logger.exception("[disparo] erro no contato %s: %s", telefone, e)
                try:
                    await repo.inserir_disparo(
                        campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                        status="falhou", mensagem_enviada=None, erro=str(e)[:500],
                    )
                    await repo.incrementar_contadores(campanha_id, falhas=1)
                except Exception:
                    pass
                falhas += 1

            # Intervalo entre disparos (não dorme depois do último).
            if i < len(contatos) - 1:
                await asyncio.sleep(intervalo)

        if pausado:
            logger.info(
                "[disparo] campanha %s interrompida (pausada): %d enviados, %d falhas nesta rodada",
                campanha_id, enviados, falhas,
            )
            return  # mantém status 'pausada'

        final = "falhou" if (enviados == 0 and falhas > 0) else "concluida"
        await repo.atualizar_status_campanha(campanha_id, final)
        logger.info(
            "[disparo] campanha %s finalizada: %d enviados, %d falhas",
            campanha_id, enviados, falhas,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("[disparo] erro fatal na campanha %s: %s", campanha_id, e)
        try:
            await repo.atualizar_status_campanha(campanha_id, "falhou")
        except Exception:
            pass
