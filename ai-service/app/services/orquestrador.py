"""Orquestrador de disparo de campanha.

Roda em background: percorre os contatos do público da campanha, gera/monta a
mensagem (IA ou manual), envia pela UAzAPI, grava o disparo e atualiza os
contadores — respeitando o intervalo configurado entre os envios.

Seleção de canal — três modos (mutuamente exclusivos):
  • Canal único: usa só o canal vinculado à campanha.
  • Roteamento (usar_roteamento): failover. Usa um canal por vez; quando ele
    acumula THRESHOLD_BLOQUEIO falhas é considerado bloqueado e sai da rotação.
  • Alternância (alternar_canais): round-robin. Cada contato sai por um canal
    diferente, distribuindo a carga entre todos os conectados.

Em ambos os modos multi-canal, cada contato tem failover: se o canal escolhido
falhar no envio, o MESMO contato é tentado imediatamente no próximo canal
disponível antes de ser marcado como falha. Canais que acumulam o limite de
falhas saem da rotação e o evento é registrado nos logs da campanha.
"""

import asyncio
import json
import logging
import re

from app.db.redis import get_redis
from app.graph.build import gerar_mensagem, registrar_no_contexto
from app.services import repo
from app.services.uazapi import enviar_texto
from app.services import followup as fu_service

logger = logging.getLogger("uvicorn.error")

# Falhas consecutivas no mesmo canal para considerá-lo bloqueado (sai da rotação).
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


def _nome_canal(c: dict) -> str:
    return c.get("phone") or c.get("uazapi_instance_name") or str(c["id"])


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
        alternar = bool(campanha.get("alternar_canais"))
        multi = usar_roteamento or alternar

        if not multi and not campanha.get("canal_id"):
            logger.error("[disparo] campanha %s sem canal vinculado", campanha_id)
            return

        # Claim atômico: evita disparo duplicado (clique duplo / múltiplos workers).
        if not await repo.claim_campanha(campanha_id):
            logger.warning("[disparo] campanha %s já reivindicada — ignorando", campanha_id)
            return

        usuario_id = campanha["usuario_id"]
        uid = str(usuario_id)

        # ── Montar lista de canais ──────────────────────────────────────────
        if multi:
            canais = await repo.get_canais_conectados(usuario_id)
            canais = [c for c in canais if c.get("uazapi_token")]
            if not canais:
                modo_nome = "alternância" if alternar else "roteamento"
                msg = f"Nenhum canal conectado disponível para {modo_nome}"
                logger.error("[disparo] %s (campanha %s)", msg, campanha_id)
                await _log(campanha_id, uid, "erro", msg)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return
            estrategia = "alternância (round-robin)" if alternar else "roteamento (failover)"
            await _log(
                campanha_id, uid, "info",
                f"{estrategia.capitalize()} — {len(canais)} canal(is) conectado(s)",
                detalhe=", ".join(_nome_canal(c) for c in canais),
            )
            if len(canais) < 2:
                await _log(
                    campanha_id, uid, "aviso",
                    "Apenas 1 canal conectado no momento do disparo — operando sem distribuição",
                    canal_id=str(canais[0]["id"]),
                )
        else:
            instancia = await repo.get_instancia(campanha["canal_id"])
            if not instancia or not instancia.get("uazapi_token"):
                logger.error("[disparo] instância/token indisponível para campanha %s", campanha_id)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return
            canais = [instancia]

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
            openai_key = await repo.get_openai_key(uid) or get_settings().OPENAI_API_KEY
            if not openai_key:
                msg = "Chave OpenAI não configurada. Acesse Configurações → Integrações e informe sua chave."
                logger.error("[disparo] %s (campanha %s, usuário %s)", msg, campanha_id, usuario_id)
                await _log(campanha_id, uid, "erro", "Chave OpenAI ausente", detalhe=msg)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return

        # ── Estado de seleção de canal ──────────────────────────────────────
        # falhas_por_canal: id -> falhas consecutivas; ao atingir o limite o canal
        # é considerado bloqueado e removido de `canais_disp()`.
        falhas_por_canal: dict[str, int] = {}
        rr = 0          # ponteiro round-robin (modo alternância)
        ultimo_canal = canais[0]   # último canal que enviou com sucesso (p/ follow-up)

        def canais_disp() -> list[dict]:
            return [c for c in canais if falhas_por_canal.get(str(c["id"]), 0) < THRESHOLD_BLOQUEIO]

        if alternar:
            estrategia_label = "alternância"
        elif usar_roteamento:
            estrategia_label = "roteamento"
        else:
            estrategia_label = "canal único"

        retomada = len(ja_enviados) > 0
        await _log(
            campanha_id, uid, "info",
            "Retomada após falha" if retomada else "Disparo iniciado",
            detalhe=(
                f"{len(contatos)} contatos | {len(ja_enviados)} já enviados (ignorados) | "
                f"modo={modo} | intervalo={intervalo}s | estratégia={estrategia_label}"
            ) if retomada else (
                f"{len(contatos)} contatos | modo={modo} | intervalo={intervalo}s | estratégia={estrategia_label}"
            ),
            canal_id=str(canais[0]["id"]),
        )
        logger.info(
            "[disparo] iniciando campanha %s (%d contatos, modo=%s, intervalo=%ds, estrategia=%s, canais=%d)",
            campanha_id, len(contatos), modo, intervalo, estrategia_label, len(canais),
        )

        enviados = 0
        falhas = 0
        pausado = False

        for i, contato in enumerate(contatos):
            # Pausa detectada pelo painel
            if await repo.get_campanha_status(campanha_id) == "pausada":
                pausado = True
                logger.info("[disparo] campanha %s pausada — interrompendo", campanha_id)
                await _log(campanha_id, uid, "aviso", "Campanha pausada pelo usuário")
                break

            # Retomada: pula quem já recebeu
            if str(contato["id"]) in ja_enviados:
                continue

            # Canais ainda disponíveis neste momento
            disp = canais_disp()
            if not disp:
                msg = "Todos os canais foram bloqueados — campanha interrompida"
                logger.error("[disparo] %s (campanha %s)", msg, campanha_id)
                await _log(campanha_id, uid, "erro", msg)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return

            telefone = _formatar_telefone(contato.get("telefone") or "")
            if not telefone or len(telefone) < 10:
                await repo.inserir_disparo(
                    campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                    status="falhou", mensagem_enviada=None, erro="Telefone inválido",
                )
                await repo.incrementar_contadores(campanha_id, falhas=1)
                falhas += 1
                continue

            # ── Ordem de tentativa de canais para ESTE contato ───────────────
            # Alternância: começa pelo próximo do round-robin; demais como fallback.
            # Roteamento/único: começa pelo primeiro disponível; demais como fallback.
            if alternar:
                inicio = disp[rr % len(disp)]
                rr += 1
            else:
                inicio = disp[0]
            ordem = [inicio] + [c for c in disp if str(c["id"]) != str(inicio["id"])]

            # Gera a mensagem uma única vez (reutilizada caso haja failover de canal).
            tid_inicial = thread_id_de(telefone, uid, str(inicio["id"]))
            try:
                if modo == "ia":
                    mensagem = await gerar_mensagem(
                        graph, thread_id=tid_inicial,
                        nome=contato.get("nome") or "",
                        observacao=contato.get("observacao") or "",
                        api_key=openai_key,
                    )
                else:
                    mensagem = _interpolar(campanha.get("mensagem") or "", contato)
            except Exception as e:
                logger.exception("[disparo] erro ao gerar mensagem p/ %s: %s", telefone, e)
                await repo.inserir_disparo(
                    campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                    status="falhou", mensagem_enviada=None, erro=str(e)[:500],
                )
                await repo.incrementar_contadores(campanha_id, falhas=1)
                falhas += 1
                if i < len(contatos) - 1:
                    await asyncio.sleep(intervalo)
                continue

            # ── Tentativa de envio com failover por canal ────────────────────
            enviado_ok = False
            canal_usado = inicio
            ultimo_status_code = None
            for canal_try in ordem:
                cid = str(canal_try["id"])
                if falhas_por_canal.get(cid, 0) >= THRESHOLD_BLOQUEIO:
                    continue  # já bloqueado
                try:
                    resultado = await enviar_texto(
                        token=canal_try["uazapi_token"], numero=telefone, texto=mensagem,
                    )
                    ultimo_status_code = resultado.get("status_code")
                    if resultado["sucesso"]:
                        enviado_ok = True
                        canal_usado = canal_try
                        falhas_por_canal[cid] = 0
                        break
                    # Falha de envio neste canal
                    falhas_por_canal[cid] = falhas_por_canal.get(cid, 0) + 1
                except Exception as e:
                    logger.warning("[disparo] erro ao enviar via canal %s: %s", _nome_canal(canal_try), e)
                    falhas_por_canal[cid] = falhas_por_canal.get(cid, 0) + 1

                # Canal atingiu o limite → bloqueado, registra e segue para o próximo
                if falhas_por_canal[cid] >= THRESHOLD_BLOQUEIO:
                    restantes = len(canais_disp())
                    aviso = (
                        f"Canal {_nome_canal(canal_try)} atingiu {THRESHOLD_BLOQUEIO} falhas — "
                        f"removido da rotação ({restantes} canal(is) restante(s))"
                    )
                    logger.warning("[disparo] %s", aviso)
                    await _log(campanha_id, uid, "aviso", "Canal bloqueado",
                               detalhe=aviso, canal_id=cid)

                # Em canal único não há failover.
                if not multi:
                    break

            instancia_id = canal_usado["id"]
            tid = thread_id_de(telefone, uid, str(instancia_id))

            await repo.inserir_disparo(
                campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                status="enviado" if enviado_ok else "falhou",
                mensagem_enviada=mensagem if enviado_ok else None,
                erro=None if enviado_ok else f"UAzAPI HTTP {ultimo_status_code}",
                canal_id=str(instancia_id),
            )

            if enviado_ok:
                enviados += 1
                ultimo_canal = canal_usado
                await repo.incrementar_contadores(campanha_id, enviados=1)
                # Salva contexto no canal que de fato enviou (p/ o webhook resolver a resposta).
                try:
                    await redis.set(
                        f"conv:{tid}",
                        json.dumps({
                            "campanha_id": str(campanha_id),
                            "contato_id": str(contato["id"]),
                            "usuario_id": uid,
                            "instancia_id": str(instancia_id),
                            "telefone": telefone,
                        }),
                        ex=60 * 60 * 24 * 30,
                    )
                except Exception as e:
                    logger.warning("[disparo] envio OK mas falhou ao salvar contexto (%s): %s", telefone, e)
                # Garante que a thread do canal que DE FATO enviou tenha a mensagem no
                # histórico (essencial p/ follow-ups de IA e p/ resolver a resposta do
                # cliente). Casos:
                #  • manual: a IA não gravou nada → registra sempre.
                #  • IA com failover (tid != tid_inicial): a IA gravou na thread do canal
                #    inicial, que não foi o usado → registra na thread correta.
                #  • IA sem failover: gerar_mensagem já gravou na thread certa → nada a fazer.
                if modo != "ia" or tid != tid_inicial:
                    try:
                        await registrar_no_contexto(graph, thread_id=tid, texto=mensagem)
                    except Exception as e:
                        logger.warning("[disparo] falha ao registrar contexto (%s): %s", telefone, e)
            else:
                falhas += 1
                await repo.incrementar_contadores(campanha_id, falhas=1)

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

        # Agenda follow-up etapa 1 para os contatos que receberam a mensagem.
        if final == "concluida":
            try:
                contatos_enviados = await repo.get_contatos_ja_enviados(campanha_id)
                if contatos_enviados:
                    await fu_service.agendar_etapa1(
                        app=app,
                        campanha_id=campanha_id,
                        usuario_id=uid,
                        canal_id=str(ultimo_canal["id"]),
                        contatos_ids=list(contatos_enviados),
                    )
            except Exception as e:
                logger.warning("[disparo] erro ao agendar follow-up (não crítico): %s", e)

        ativos = len(canais_disp())
        await _log(
            campanha_id, uid, "info", "Disparo concluído",
            detalhe=f"{enviados} enviados | {falhas} falhas | {ativos}/{len(canais)} canal(is) ativo(s) ao final",
            canal_id=str(ultimo_canal["id"]),
        )
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
