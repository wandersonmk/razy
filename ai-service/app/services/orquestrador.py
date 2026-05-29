"""Orquestrador de disparo de campanha.

Roda em background: percorre os contatos do público da campanha, gera/monta a
mensagem (IA ou manual), envia pela UAzAPI, grava o disparo e atualiza os
contadores — respeitando o intervalo configurado entre os envios.

Roteamento automático (usar_roteamento=True):
  Carrega todos os canais conectados do usuário. Se um canal acumular
  THRESHOLD_BLOQUEIO falhas consecutivas, considera-o bloqueado, registra
  o evento nos logs e troca para o próximo canal disponível. O disparo
  continua do ponto onde parou, sem reenviar contatos já atendidos.
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

# Número de falhas consecutivas no mesmo canal para acionar troca
THRESHOLD_BLOQUEIO = 3

# Mantém referência das tasks em andamento (evita coleta pelo GC).
_tasks: set[asyncio.Task] = set()


def thread_id_de(telefone: str, usuario_id: str, instancia_id: str) -> str:
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


async def _log(campanha_id: str, usuario_id: str, nivel: str, evento: str,
               detalhe: str | None = None, canal_id: str | None = None) -> None:
    """Grava um evento no log da campanha (silencia erros para não derrubar o disparo)."""
    try:
        await repo.inserir_log_campanha(
            campanha_id=campanha_id, usuario_id=usuario_id,
            nivel=nivel, evento=evento, detalhe=detalhe, canal_id=canal_id,
        )
    except Exception as e:
        logger.warning("[log] falha ao gravar log da campanha %s: %s", campanha_id, e)


async def _disparar(app, campanha_id: str) -> None:
    try:
        campanha = await repo.get_campanha(campanha_id)
        if not campanha:
            logger.error("[disparo] campanha %s não encontrada", campanha_id)
            return

        usar_roteamento = bool(campanha.get("usar_roteamento"))

        if not usar_roteamento and not campanha.get("canal_id"):
            logger.error("[disparo] campanha %s sem canal vinculado", campanha_id)
            return

        # Claim atômico: evita disparo duplicado (clique duplo / múltiplos workers).
        if not await repo.claim_campanha(campanha_id):
            logger.warning("[disparo] campanha %s já reivindicada — ignorando", campanha_id)
            return

        usuario_id = campanha["usuario_id"]

        # ── Montar lista de canais disponíveis ──────────────────────────────
        if usar_roteamento:
            canais_lista = await repo.get_canais_conectados(usuario_id)
            if not canais_lista:
                logger.error("[disparo] roteamento ativado mas nenhum canal conectado (campanha %s)", campanha_id)
                await _log(campanha_id, usuario_id, "erro",
                           "Nenhum canal conectado disponível para roteamento")
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return
            await _log(campanha_id, usuario_id, "info",
                       f"Roteamento ativado — {len(canais_lista)} canal(is) disponível(is)",
                       detalhe=", ".join(c.get("phone") or c.get("uazapi_instance_name") or str(c["id"]) for c in canais_lista))
        else:
            instancia = await repo.get_instancia(campanha["canal_id"])
            if not instancia or not instancia.get("uazapi_token"):
                logger.error("[disparo] instância/token indisponível para campanha %s", campanha_id)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return
            canais_lista = [instancia]

        contatos = await repo.get_contatos_do_publico(campanha["publico_id"])
        if not contatos:
            logger.warning("[disparo] público sem contatos (campanha %s)", campanha_id)
            await repo.atualizar_status_campanha(campanha_id, "concluida")
            return

        ja_enviados = await repo.get_contatos_ja_enviados(campanha_id)

        modo = campanha.get("modo_mensagem") or "manual"
        intervalo = max(1, int(campanha.get("intervalo_segundos") or 10))
        graph = app.state.graph
        redis = get_redis()
        # Chave OpenAI: obrigatória para modo IA — vem do painel (Configurações → Integrações)
        openai_key: str | None = None
        if modo == "ia":
            from app.config import get_settings
            openai_key = await repo.get_openai_key(str(usuario_id)) or get_settings().OPENAI_API_KEY
            if not openai_key:
                msg = "Chave OpenAI não configurada. Acesse Configurações → Integrações e informe sua chave."
                logger.error("[disparo] %s (campanha %s, usuário %s)", msg, campanha_id, usuario_id)
                await _log(campanha_id, str(usuario_id), "erro", "Chave OpenAI ausente", detalhe=msg)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return

        # ── Estado de roteamento ─────────────────────────────────────────────
        canal_idx = 0
        canal_atual = canais_lista[canal_idx]
        falhas_consecutivas = 0

        retomada = len(ja_enviados) > 0
        await _log(
            campanha_id, str(usuario_id), "info",
            "Retomada após falha" if retomada else "Disparo iniciado",
            detalhe=(
                f"{len(contatos)} contatos | {len(ja_enviados)} já enviados (serão ignorados) | "
                f"modo={modo} | intervalo={intervalo}s"
            ) if retomada else f"{len(contatos)} contatos | modo={modo} | intervalo={intervalo}s",
            canal_id=str(canal_atual["id"]),
        )
        logger.info(
            "[disparo] iniciando campanha %s (%d contatos, modo=%s, intervalo=%ds, roteamento=%s)",
            campanha_id, len(contatos), modo, intervalo, usar_roteamento,
        )

        enviados = 0
        falhas = 0
        pausado = False

        for i, contato in enumerate(contatos):
            # Pausa detectada pelo painel
            if await repo.get_campanha_status(campanha_id) == "pausada":
                pausado = True
                logger.info("[disparo] campanha %s pausada — interrompendo", campanha_id)
                await _log(campanha_id, usuario_id, "aviso", "Campanha pausada pelo usuário")
                break

            # Retomada: pula quem já recebeu
            if str(contato["id"]) in ja_enviados:
                continue

            # ── Verificar se precisa rotear ──────────────────────────────────
            if usar_roteamento and falhas_consecutivas >= THRESHOLD_BLOQUEIO:
                canal_bloqueado = canal_atual
                canal_idx += 1
                if canal_idx >= len(canais_lista):
                    msg = "Todos os canais esgotados/bloqueados — campanha interrompida"
                    logger.error("[disparo] %s (campanha %s)", msg, campanha_id)
                    await _log(campanha_id, usuario_id, "erro", msg,
                               canal_id=str(canal_bloqueado["id"]))
                    await repo.atualizar_status_campanha(campanha_id, "falhou")
                    return

                canal_atual = canais_lista[canal_idx]
                falhas_consecutivas = 0
                num_bloqueado = canal_bloqueado.get("phone") or canal_bloqueado.get("uazapi_instance_name") or str(canal_bloqueado["id"])
                num_novo = canal_atual.get("phone") or canal_atual.get("uazapi_instance_name") or str(canal_atual["id"])
                aviso = f"Canal {num_bloqueado} detectado como bloqueado após {THRESHOLD_BLOQUEIO} falhas consecutivas → roteando para {num_novo}"
                logger.warning("[disparo] %s", aviso)
                await _log(campanha_id, usuario_id, "aviso", "Roteamento de canal",
                           detalhe=aviso, canal_id=str(canal_atual["id"]))

            token = canal_atual["uazapi_token"]
            instancia_id = canal_atual["id"]

            telefone = _formatar_telefone(contato.get("telefone") or "")
            if not telefone or len(telefone) < 10:
                await repo.inserir_disparo(
                    campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                    status="falhou", mensagem_enviada=None, erro="Telefone inválido",
                )
                await repo.incrementar_contadores(campanha_id, falhas=1)
                falhas += 1
                continue

            tid = thread_id_de(telefone, str(usuario_id), str(instancia_id))

            try:
                if modo == "ia":
                    mensagem = await gerar_mensagem(
                        graph, thread_id=tid,
                        nome=contato.get("nome") or "",
                        observacao=contato.get("observacao") or "",
                        api_key=openai_key,
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
                    falhas_consecutivas = 0
                    await repo.incrementar_contadores(campanha_id, enviados=1)
                    try:
                        await redis.set(
                            f"conv:{tid}",
                            json.dumps({
                                "campanha_id": str(campanha_id),
                                "contato_id": str(contato["id"]),
                                "usuario_id": str(usuario_id),
                                "instancia_id": str(instancia_id),
                                "telefone": telefone,
                            }),
                            ex=60 * 60 * 24 * 30,
                        )
                    except Exception as e:
                        logger.warning("[disparo] envio OK mas falhou ao salvar contexto (%s): %s", telefone, e)
                else:
                    falhas_consecutivas += 1
                    falhas += 1
                    await repo.incrementar_contadores(campanha_id, falhas=1)

            except Exception as e:
                logger.exception("[disparo] erro no contato %s: %s", telefone, e)
                falhas_consecutivas += 1
                falhas += 1
                try:
                    await repo.inserir_disparo(
                        campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                        status="falhou", mensagem_enviada=None, erro=str(e)[:500],
                    )
                    await repo.incrementar_contadores(campanha_id, falhas=1)
                except Exception:
                    pass

            # Intervalo entre disparos (não dorme depois do último)
            if i < len(contatos) - 1:
                await asyncio.sleep(intervalo)

        if pausado:
            logger.info(
                "[disparo] campanha %s interrompida (pausada): %d enviados, %d falhas nesta rodada",
                campanha_id, enviados, falhas,
            )
            return

        final = "falhou" if (enviados == 0 and falhas > 0) else "concluida"
        await repo.atualizar_status_campanha(campanha_id, final)

        canal_nome = canal_atual.get("phone") or canal_atual.get("uazapi_instance_name") or str(canal_atual["id"])
        await _log(campanha_id, usuario_id, "info",
                   "Disparo concluído",
                   detalhe=f"{enviados} enviados | {falhas} falhas | canal final: {canal_nome}",
                   canal_id=str(canal_atual["id"]))
        logger.info(
            "[disparo] campanha %s finalizada: %d enviados, %d falhas",
            campanha_id, enviados, falhas,
        )

    except Exception as e:
        logger.exception("[disparo] erro fatal na campanha %s: %s", campanha_id, e)
        try:
            await repo.atualizar_status_campanha(campanha_id, "falhou")
        except Exception:
            pass
