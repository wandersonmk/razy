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

import httpx
from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage

from app.config import get_settings
from app.db.redis import get_redis
from app.services import repo
from app.services.assistente import responder_como_assistente, transcrever_audio
from app.services.uazapi import enviar_texto

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["webhook"])


def _phone_digits(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\D", "", s.split("@")[0])


def _eh_audio(msg: dict) -> bool:
    tipo = (msg.get("messageType") or msg.get("type") or msg.get("mediaType") or "").lower()
    if "audio" in tipo or "ptt" in tipo:
        return True
    return bool(msg.get("audio"))


async def _baixar_audio(msg: dict) -> tuple[bytes | None, str]:
    """Best-effort: extrai os bytes do áudio do payload (URL direta ou base64).

    A estrutura exata do payload de mídia da UAzAPI é confirmada via logs; esta
    função tenta os campos mais comuns e registra o que encontrar para ajuste fino.
    """
    audio = msg.get("audio") if isinstance(msg.get("audio"), dict) else {}

    # 1) URL direta para download
    url = (
        msg.get("mediaUrl") or msg.get("url") or msg.get("downloadUrl")
        or audio.get("url") or audio.get("mediaUrl")
    )
    if url and isinstance(url, str) and url.startswith("http"):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(url)
                if r.status_code < 400 and r.content:
                    return r.content, "audio.ogg"
        except Exception as e:
            logger.warning("[webhook] falha ao baixar áudio por URL: %s", e)

    # 2) base64 embutido
    b64 = (
        msg.get("base64") or msg.get("content") or msg.get("body")
        or audio.get("base64") or audio.get("data")
    )
    if b64 and isinstance(b64, str) and len(b64) > 100:
        try:
            if "," in b64 and b64.strip().startswith("data:"):
                b64 = b64.split(",", 1)[1]
            return base64.b64decode(b64), "audio.ogg"
        except Exception as e:
            logger.warning("[webhook] falha ao decodificar áudio base64: %s", e)

    logger.warning("[webhook] áudio recebido mas não consegui extrair os bytes. Campos: %s", list(msg.keys()))
    return None, "audio.ogg"


async def _notificar_atendente(*, token: str, atendente_tel: str, cliente_tel: str, resumo: str | None) -> None:
    numero = _phone_digits(atendente_tel)
    if not numero:
        return
    texto = (
        "🔔 *Novo cliente aguardando atendimento*\n\n"
        f"📱 Cliente: {cliente_tel}\n\n"
        f"📋 Resumo do atendimento:\n{resumo or '(sem resumo)'}"
    )
    try:
        await enviar_texto(token=token, numero=numero, texto=texto)
        logger.info("[webhook] atendente %s notificado sobre cliente %s", numero, cliente_tel)
    except Exception as e:
        logger.warning("[webhook] falha ao notificar atendente: %s", e)


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
    if msg.get("fromMe") or msg.get("isGroup"):
        return {"status": "ok", "ignored": "fromMe/group"}

    phone = _phone_digits(msg.get("sender_pn") or msg.get("chatid"))
    token = payload.get("token")

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

        # Chave OpenAI do usuário (necessária para transcrição e assistente).
        openai_key = await repo.get_openai_key(usuario_id) or get_settings().OPENAI_API_KEY

        # ── Texto da mensagem (transcreve áudio se necessário) ───────────────
        texto = (msg.get("text") or "").strip()
        if not texto and _eh_audio(msg):
            if not openai_key:
                logger.warning("[webhook] áudio recebido mas sem chave OpenAI para transcrever")
                return {"status": "ok", "ignored": "audio sem openai key"}
            audio_bytes, fname = await _baixar_audio(msg)
            if audio_bytes:
                texto = await transcrever_audio(audio_bytes=audio_bytes, filename=fname, api_key=openai_key)

        if not texto:
            logger.info("[webhook] mensagem de %s sem texto utilizável (tipo não suportado)", phone)
            return {"status": "ok", "ignored": "sem texto"}

        logger.info("[webhook] resposta de %s: %r", phone, texto)

        # ── Contexto de disparo (registro de resposta + cancelar follow-ups) ──
        redis = get_redis()
        raw = await redis.get(f"conv:{tid}")
        ctx = json.loads(raw) if raw else None
        if ctx:
            await repo.registrar_resposta_contato(
                campanha_id=ctx["campanha_id"], contato_id=ctx["contato_id"], resposta_texto=texto,
            )
            await repo.incrementar_respostas(ctx["campanha_id"])
            try:
                await repo.cancelar_followups_contato(
                    campanha_id=ctx["campanha_id"], contato_id=ctx["contato_id"],
                )
            except Exception as e:
                logger.warning("[webhook] erro ao cancelar follow-ups: %s", e)
            logger.info("[webhook] resposta registrada — campanha=%s contato=%s", ctx["campanha_id"], ctx["contato_id"])

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
            except Exception as e:
                logger.warning("[webhook] falha ao enviar resposta do assistente: %s", e)

            # Handoff: coleta completa → notifica o atendente com o resumo.
            if resultado.coleta_completa and (assistente.get("atendente_telefone") or "").strip():
                await _notificar_atendente(
                    token=instancia["uazapi_token"],
                    atendente_tel=assistente["atendente_telefone"],
                    cliente_tel=phone,
                    resumo=resultado.resumo_atendimento,
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
