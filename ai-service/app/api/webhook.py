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
"""

import base64
import json
import logging
import re

from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage

from app.config import get_settings
from app.db.redis import get_redis
from app.services import repo
from app.services.assistente import (
    consumir_eco,
    esta_pausado,
    marcar_saida,
    pausar_atendimento,
    responder_como_assistente,
    transcrever_audio,
)
from app.services.uazapi import baixar_midia, enviar_texto

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

    try:
        instancia = await repo.get_instancia_by_token(token)
        if not instancia:
            logger.warning("[webhook] instância não encontrada para o token recebido")
            return {"status": "ok", "ignored": "instancia desconhecida"}

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
                return {"status": "ok", "echo": True}  # nosso próprio envio
            assistente_cfg = await repo.get_assistente(usuario_id)
            if assistente_cfg and assistente_cfg.get("pausa_ativa"):
                minutos = int(assistente_cfg.get("pausa_minutos") or 30)
                await pausar_atendimento(redis, tid, minutos)
                logger.info("[webhook] dono respondeu %s manualmente — IA pausada por %dmin", phone, minutos)
            return {"status": "ok", "pausa": True}

        # Chave OpenAI do usuário (necessária para transcrição e assistente).
        openai_key = await repo.get_openai_key(usuario_id) or get_settings().OPENAI_API_KEY

        # ── Texto da mensagem (transcreve áudio se necessário) ───────────────
        texto = (msg.get("text") or "").strip()
        if not texto and _eh_audio(msg):
            if not openai_key:
                logger.warning("[webhook] áudio recebido mas sem chave OpenAI para transcrever")
                return {"status": "ok", "ignored": "audio sem openai key"}
            message_id = _message_id(msg)
            if not message_id:
                logger.warning("[webhook] áudio sem id de mensagem. Campos: %s", list(msg.keys()))
                return {"status": "ok", "ignored": "audio sem id"}
            texto = await _transcrever_via_uazapi(token=token, message_id=message_id, openai_key=openai_key)
            if texto:
                logger.info("[webhook] áudio de %s transcrito: %r", phone, texto)

        if not texto:
            logger.info("[webhook] mensagem de %s sem texto utilizável (tipo não suportado)", phone)
            return {"status": "ok", "ignored": "sem texto"}

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

        # ── Pausa: dono assumiu a conversa manualmente → IA não responde ──────
        if await esta_pausado(redis, tid):
            logger.info("[webhook] atendimento de %s está pausado — IA não responde", phone)
            try:
                await request.app.state.graph.aupdate_state(
                    {"configurable": {"thread_id": tid}},
                    {"messages": [HumanMessage(content=texto)]},
                )
            except Exception:
                pass
            return {"status": "ok", "pausado": True}

        # ── Assistente de IA (atendimento automático) ────────────────────────
        assistente = await repo.get_assistente(usuario_id)
        if assistente and assistente.get("ativo") and openai_key:
            resultado = await responder_como_assistente(
                request.app.state.graph,
                thread_id=tid,
                cfg=assistente,
                texto_cliente=texto,
                api_key=openai_key,
            )
            # Responde o cliente pelo MESMO número (instância) que recebeu.
            try:
                await enviar_texto(token=instancia["uazapi_token"], numero=phone, texto=resultado.resposta)
                # Marca como nosso envio para ignorar o eco fromMe (não auto-pausar).
                await marcar_saida(redis, tid, resultado.resposta)
            except Exception as e:
                logger.warning("[webhook] falha ao enviar resposta do assistente: %s", e)

            # Handoff: coleta completa → notifica os atendentes com o resumo.
            if resultado.coleta_completa and (assistente.get("atendente_telefone") or "").strip():
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
            return {"status": "ok", "assistente": True}

        # Assistente inativo: apenas mantém o contexto da conversa para uso futuro.
        try:
            await request.app.state.graph.aupdate_state(
                {"configurable": {"thread_id": tid}},
                {"messages": [HumanMessage(content=texto)]},
            )
        except Exception as e:
            logger.warning("[webhook] falha ao atualizar memória do grafo: %s", e)

        return {"status": "ok", "registrado": ctx is not None}
    except Exception as e:
        logger.exception("[webhook] erro ao processar resposta: %s", e)
        return {"status": "ok", "erro": True}
