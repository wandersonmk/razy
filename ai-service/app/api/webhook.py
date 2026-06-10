"""Webhook de recebimento da UAzAPI (respostas do cliente).

Fluxo:
  1. UAzAPI faz POST aqui quando chega mensagem (EventType=messages).
  2. Ignora mensagens enviadas por nós (fromMe) e grupos.
  3. Resolve a instância pelo token do payload → usuario_id + instancia_id.
  4. Se for áudio, transcreve via OpenAI (whisper) e segue como texto.
  5. Reconstrói thread_id e, havendo contexto de disparo, registra a resposta
     (resposta_texto/respondido_em), incrementa total_respostas e cancela follow-ups.
  6. Se o assistente estiver ativo, gera a resposta de atendimento (mantendo o
     contexto da conversa), envia ao cliente e — quando a coleta termina —
     encaminha o resumo ao número do atendente configurado.

O webhook responde 200 IMEDIATAMENTE e faz o trabalho pesado (transcrição, LLM,
envio) em segundo plano — ver `_processar_evento`. Isso evita que a UAzAPI estoure
o timeout do webhook e reentregue o evento, o que saturava os workers e (com a
trava de idempotência mal posicionada) fazia respostas ao cliente se perderem.
"""

import asyncio
import base64
import json
import logging
import re

from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage

from app.config import get_settings
from app.db.redis import get_redis
from app.graph.build import LLM_NODE
from app.services import repo
from app.services.assistente import (
    consumir_eco,
    detectar_loop_mensagem,
    esta_pausado,
    marcar_saida,
    pausar_atendimento,
    responder_como_assistente,
    transcrever_audio,
)
from app.services.uazapi import baixar_midia, enviar_presenca, enviar_texto

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["webhook"])


def _phone_digits(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\D", "", s.split("@")[0])


_AUDIO_HINTS = ("audio", "ptt", "voice", "ogg", "mpeg", "mp3")


def _eh_audio(msg: dict) -> bool:
    campos = " ".join(
        str(msg.get(k) or "") for k in ("messageType", "type", "mediaType", "mimetype", "mimeType")
    ).lower()
    if any(h in campos for h in _AUDIO_HINTS):
        return True
    return bool(msg.get("audio"))


def _message_id(msg: dict) -> str | None:
    key = msg.get("key") if isinstance(msg.get("key"), dict) else {}
    return msg.get("messageid") or msg.get("id") or msg.get("messageId") or key.get("id")


async def _transcrever_via_uazapi(*, token: str, message_id: str, openai_key: str | None) -> str:
    """Baixa o áudio pela UAzAPI e transcreve.

    Caminho principal: pede a transcrição direto à UAzAPI (transcribe=true). Se vier
    vazia, faz fallback baixando o base64 e transcrevendo localmente (whisper).
    """
    data = await baixar_midia(token=token, message_id=message_id, transcribe=True, openai_apikey=openai_key)
    if data.get("error"):
        logger.warning("[webhook] /message/download falhou: %s", data.get("error"))
        return ""

    texto = (data.get("transcription") or "").strip()
    if texto:
        return texto

    # Fallback: transcrever localmente a partir do base64
    b64 = data.get("base64Data") or data.get("base64")
    if b64 and openai_key:
        try:
            if isinstance(b64, str) and b64.startswith("data:") and "," in b64:
                b64 = b64.split(",", 1)[1]
            audio_bytes = base64.b64decode(b64)
            return await transcrever_audio(audio_bytes=audio_bytes, filename="audio.mp3", api_key=openai_key)
        except Exception as e:
            logger.warning("[webhook] falha no fallback de transcrição local: %s", e)
    return ""


def _formatar_tel(t: str) -> str:
    nums = re.sub(r"\D", "", t or "")
    if nums.startswith("55") and len(nums) >= 12:
        return nums
    if len(nums) in (10, 11):
        return "55" + nums
    return nums


async def _notificar_atendentes(
    *,
    token: str,
    atendente_tel: str,
    cliente_tel: str,
    resumo: str | None,
    rotativo: bool,
    usuario_id: str,
) -> None:
    """Notifica os atendentes configurados (lista separada por vírgula).

    rotativo=False → notifica TODOS. rotativo=True → notifica apenas o próximo da
    fila (round-robin persistido no Redis por usuário).
    """
    numeros = [_formatar_tel(n) for n in (atendente_tel or "").split(",")]
    numeros = [n for n in numeros if len(n) >= 12]
    if not numeros:
        return

    if rotativo and len(numeros) > 1:
        idx = 0
        try:
            redis = get_redis()
            idx = (await redis.incr(f"atendente_rr:{usuario_id}") - 1) % len(numeros)
        except Exception as e:
            logger.warning("[webhook] falha no rodízio (usando o 1º): %s", e)
            idx = 0
        alvos = [numeros[idx]]
    else:
        alvos = numeros

    texto = (
        "🔔 *Novo cliente aguardando atendimento*\n\n"
        f"📱 Cliente: {cliente_tel}\n\n"
        f"📋 Resumo do atendimento:\n{resumo or '(sem resumo)'}"
    )
    for numero in alvos:
        try:
            await enviar_texto(token=token, numero=numero, texto=texto)
            logger.info("[webhook] atendente %s notificado sobre cliente %s", numero, cliente_tel)
        except Exception as e:
            logger.warning("[webhook] falha ao notificar atendente %s: %s", numero, e)


@router.post("/webhook/uazapi")
async def webhook_uazapi(request: Request):
    """Valida o básico e responde 200 IMEDIATAMENTE; o atendimento roda em background.

    O trabalho real (transcrição + LLM + 'digitando' + envio) leva ~10-15s. Fazê-lo
    antes de responder estourava o timeout do webhook da UAzAPI, que reentregava o
    evento e saturava os 2 workers. Aqui só fazemos filtros baratos e agendamos o
    processamento; ver `_processar_evento`.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "non-json"}

    event = payload.get("EventType")
    msg = payload.get("message") or {}
    if event and event != "messages":
        return {"status": "ok", "ignored": f"event:{event}"}
    if msg.get("isGroup"):
        return {"status": "ok", "ignored": "group"}

    token = payload.get("token")
    eh_from_me = bool(msg.get("fromMe"))
    # Telefone do CLIENTE: em mensagens recebidas é o sender; nas enviadas (fromMe)
    # é o destinatário (chatid).
    if eh_from_me:
        phone = _phone_digits(msg.get("chatid") or msg.get("sender_pn"))
    else:
        phone = _phone_digits(msg.get("sender_pn") or msg.get("chatid"))

    if not (phone and token):
        return {"status": "ok", "ignored": "campos ausentes"}

    if getattr(request.app.state, "supabase", None) is None:
        logger.warning("[webhook] Supabase indisponível — ignorado")
        return {"status": "ok", "ignored": "supabase off"}

    _agendar_processamento(
        request.app, payload=payload, msg=msg, token=token, phone=phone, eh_from_me=eh_from_me,
    )
    return {"status": "ok", "queued": True}


def _agendar_processamento(app, **kwargs) -> None:
    """Agenda o processamento do evento em segundo plano.

    Guarda a referência da task num set no app.state — sem isso o garbage collector
    pode coletar a task antes de ela terminar (asyncio mantém só referência fraca).
    A referência é removida automaticamente ao concluir. O set é drenado no shutdown
    (ver `_drenar_webhooks` em main.py) para não perder envios em andamento.
    """
    tasks = getattr(app.state, "webhook_tasks", None)
    if tasks is None:
        tasks = set()
        app.state.webhook_tasks = tasks
    task = asyncio.create_task(_processar_evento(app, **kwargs))
    tasks.add(task)
    task.add_done_callback(tasks.discard)


async def _processar_evento(
    app, *, payload: dict, msg: dict, token: str, phone: str, eh_from_me: bool
) -> None:
    """Processa o evento já fora do ciclo de request/response (segundo plano).

    Aqui mora todo o trabalho pesado: idempotência, transcrição de áudio, registro
    da resposta, atendimento da IA, handoff e exclusão de follow-ups.
    """
    try:
        instancia = await repo.get_instancia_by_token(token)
        if not instancia:
            logger.warning("[webhook] instância não encontrada para o token recebido")
            return

        usuario_id = str(instancia["usuario_id"])
        instancia_id = str(instancia["id"])
        tid = f"{phone}_{usuario_id}_{instancia_id}"
        redis = get_redis()

        # ── Mensagem ENVIADA (fromMe) ────────────────────────────────────────
        # Pode ser eco dos nossos próprios envios (campanha/follow-up/IA) OU o
        # dono respondendo manualmente pelo celular. Se for o dono, pausa a IA.
        if eh_from_me:
            texto_out = (msg.get("text") or "").strip()
            if texto_out and await consumir_eco(redis, tid, texto_out):
                return  # nosso próprio envio
            assistente_cfg = await repo.get_assistente(usuario_id)
            if assistente_cfg and assistente_cfg.get("pausa_ativa"):
                minutos = int(assistente_cfg.get("pausa_minutos") or 30)
                await pausar_atendimento(redis, tid, minutos)
                logger.info("[webhook] dono respondeu %s manualmente — IA pausada por %dmin", phone, minutos)
            return

        # ── Idempotência: ignora reentregas da MESMA mensagem ────────────────
        # SET NX é atômico contra corridas. IMPORTANTE: se o processamento falhar
        # (erro de LLM/envio/DB), a trava é LIBERADA no `except` abaixo — senão uma
        # reentrega cairia como "duplicata" e a resposta ao cliente se perderia
        # para sempre (essa era a causa de mensagens ficarem sem resposta).
        msg_id = _message_id(msg)
        if msg_id:
            primeira_vez = await redis.set(f"msg_seen:{msg_id}", "1", nx=True, ex=600)
            if not primeira_vez:
                logger.info("[webhook] mensagem %s já processada — ignorada (duplicata)", msg_id)
                return

        try:
            # Chave OpenAI do usuário (necessária para transcrição e assistente).
            openai_key = await repo.get_openai_key(usuario_id) or get_settings().OPENAI_API_KEY

            # ── Texto da mensagem (transcreve áudio se necessário) ───────────
            texto = (msg.get("text") or "").strip()
            if not texto and _eh_audio(msg):
                if not openai_key:
                    logger.warning("[webhook] áudio recebido mas sem chave OpenAI para transcrever")
                    return
                message_id = _message_id(msg)
                if not message_id:
                    logger.warning("[webhook] áudio sem id de mensagem. Campos: %s", list(msg.keys()))
                    return
                texto = await _transcrever_via_uazapi(token=token, message_id=message_id, openai_key=openai_key)
                if texto:
                    logger.info("[webhook] áudio de %s transcrito: %r", phone, texto)

            if not texto:
                logger.info("[webhook] mensagem de %s sem texto utilizável (tipo não suportado)", phone)
                return

            logger.info("[webhook] resposta de %s: %r", phone, texto)

            # ── Contexto de disparo (registro de resposta + cancelar follow-ups) ──
            raw = await redis.get(f"conv:{tid}")
            ctx = json.loads(raw) if raw else None
            if ctx:
                primeira = await repo.registrar_resposta_contato(
                    campanha_id=ctx["campanha_id"], contato_id=ctx["contato_id"], resposta_texto=texto,
                )
                # Conta a resposta apenas na PRIMEIRA vez que o contato responde.
                if primeira:
                    await repo.incrementar_respostas(ctx["campanha_id"])
                try:
                    await repo.cancelar_followups_contato(
                        campanha_id=ctx["campanha_id"], contato_id=ctx["contato_id"],
                    )
                except Exception as e:
                    logger.warning("[webhook] erro ao cancelar follow-ups: %s", e)
                logger.info("[webhook] resposta registrada — campanha=%s contato=%s", ctx["campanha_id"], ctx["contato_id"])

            # ── Pausa: dono assumiu a conversa manualmente → IA não responde ──
            if await esta_pausado(redis, tid):
                logger.info("[webhook] atendimento de %s está pausado — IA não responde", phone)
                try:
                    await app.state.graph.aupdate_state(
                        {"configurable": {"thread_id": tid}},
                        {"messages": [HumanMessage(content=texto)]},
                        as_node=LLM_NODE,
                    )
                except Exception:
                    pass
                return

            # ── Assistente de IA (atendimento automático) ────────────────────
            assistente = await repo.get_assistente(usuario_id)
            if assistente and assistente.get("ativo") and openai_key:
                # Quebra-loop: se o contato (ex.: bot de auto-resposta do lead) repetir a
                # MESMA mensagem várias vezes seguidas, a IA para de responder àquele
                # número — evita loop infinito bot-contra-bot (gasto de tokens/mensagens).
                if await detectar_loop_mensagem(redis, tid, texto):
                    logger.info("[webhook] auto-resposta em loop detectada em %s — IA não responde", phone)
                    return

                # Mostra "digitando..." enquanto a IA elabora a resposta (humaniza).
                await enviar_presenca(token=instancia["uazapi_token"], numero=phone, presence="composing", delay_ms=8000)

                resultado = await responder_como_assistente(
                    app.state.graph,
                    thread_id=tid,
                    cfg=assistente,
                    texto_cliente=texto,
                    api_key=openai_key,
                )
                # Pausa natural proporcional ao tamanho da resposta (~digitação humana).
                await asyncio.sleep(min(4.0, max(0.8, len(resultado.resposta) * 0.03)))

                # Responde o cliente pelo MESMO número (instância) que recebeu.
                # IMPORTANTE: enviar_texto NÃO lança exceção quando a UAzAPI recusa
                # (canal desconectado, número inválido, rate limit) — retorna
                # sucesso=False. Por isso checamos o retorno e logamos explicitamente
                # se a IA conseguiu ou não responder (antes isso passava em silêncio).
                envio: dict | None = None
                try:
                    envio = await enviar_texto(token=instancia["uazapi_token"], numero=phone, texto=resultado.resposta)
                except Exception as e:
                    logger.warning("[webhook] erro ao enviar resposta da IA para %s: %s", phone, e)

                if envio and envio.get("sucesso"):
                    # Marca como nosso envio para ignorar o eco fromMe (não auto-pausar).
                    await marcar_saida(redis, tid, resultado.resposta)
                    logger.info("[webhook] IA respondeu %s: %r", phone, resultado.resposta)
                else:
                    erro = (envio or {}).get("erro", "exceção no envio")
                    logger.warning(
                        "[webhook] IA NÃO respondeu %s — falha no envio pela UAzAPI: %s", phone, erro,
                    )

                # Handoff: coleta completa → notifica os atendentes com o resumo.
                if resultado.coleta_completa and (assistente.get("atendente_telefone") or "").strip():
                    # Handoff ÚNICO por conversa: depois que a coleta termina,
                    # coleta_completa continua true nas mensagens seguintes do cliente,
                    # o que faria o atendente ser notificado a cada nova mensagem.
                    # SET NX garante que só a 1ª vez dispara (atômico contra corridas).
                    # TTL de 24h permite re-notificar se o lead voltar muito depois.
                    primeiro_handoff = await redis.set(f"handoff:{tid}", "1", nx=True, ex=86400)
                    if primeiro_handoff:
                        # Usa o canal dedicado a notificações, se houver; senão o canal da conversa.
                        canal_notif = await repo.get_canal_notificacao(usuario_id)
                        token_notif = (canal_notif or {}).get("uazapi_token") or instancia["uazapi_token"]
                        await _notificar_atendentes(
                            token=token_notif,
                            atendente_tel=assistente["atendente_telefone"],
                            cliente_tel=phone,
                            resumo=resultado.resumo_atendimento,
                            rotativo=bool(assistente.get("notificar_rotativo")),
                            usuario_id=usuario_id,
                        )
                    else:
                        logger.info("[webhook] handoff de %s já realizado — não re-notifica", phone)

                # Lead SEM interesse (negativa clara) → exclui de TODAS as sequências de
                # follow-up (atuais e futuras) para não incomodar. A IA ainda responde se
                # o lead voltar a falar; só paramos de procurá-lo proativamente.
                if resultado.sem_interesse and ctx:
                    try:
                        await repo.marcar_contato_sem_interesse(
                            contato_id=ctx["contato_id"], motivo=texto[:200],
                        )
                        await repo.cancelar_todos_followups_contato(contato_id=ctx["contato_id"])
                        logger.info(
                            "[webhook] lead %s sem interesse — excluído dos follow-ups (contato=%s)",
                            phone, ctx["contato_id"],
                        )
                    except Exception as e:
                        logger.warning("[webhook] erro ao excluir lead sem interesse: %s", e)
                return

            # Assistente inativo: apenas mantém o contexto da conversa para uso futuro.
            # Loga o motivo para deixar explícito no painel POR QUE a IA não respondeu.
            if not (assistente and assistente.get("ativo")):
                motivo = "assistente desativado nas configurações"
            elif not openai_key:
                motivo = "sem chave OpenAI configurada"
            else:
                motivo = "assistente indisponível"
            logger.info("[webhook] IA não responde %s (%s) — apenas registrei a mensagem", phone, motivo)
            try:
                await app.state.graph.aupdate_state(
                    {"configurable": {"thread_id": tid}},
                    {"messages": [HumanMessage(content=texto)]},
                    as_node=LLM_NODE,
                )
            except Exception as e:
                logger.warning("[webhook] falha ao atualizar memória do grafo: %s", e)
        except Exception:
            # Falha no processamento: libera a trava de idempotência para que uma
            # eventual reentrega da MESMA mensagem possa ser reprocessada (senão a
            # resposta ao cliente ficaria perdida para sempre).
            if msg_id:
                try:
                    await redis.delete(f"msg_seen:{msg_id}")
                except Exception:
                    pass
            raise
    except Exception as e:
        logger.exception("[webhook] erro ao processar resposta: %s", e)
