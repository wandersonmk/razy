"""Webhook de recebimento da UAzAPI (respostas do cliente).

Fluxo:
  1. UAzAPI faz POST aqui quando chega mensagem (EventType=messages).
  2. Ignora mensagens enviadas por nós (fromMe) e grupos.
  3. Resolve a instância pelo token do payload → usuario_id + instancia_id.
  4. Reconstrói thread_id = telefone_empresa_instancia e busca o contexto no Redis.
  5. Registra a resposta (resposta_texto/respondido_em) e incrementa total_respostas.
  6. Anexa a resposta à memória do grafo (sem gerar resposta automática).
"""

import json
import logging
import re

from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage

from app.db.redis import get_redis
from app.services import repo

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["webhook"])


def _phone_digits(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\D", "", s.split("@")[0])


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
    text = msg.get("text") or ""
    token = payload.get("token")

    logger.info("[webhook] resposta de %s: %r", phone, text)

    if not (phone and text and token):
        return {"status": "ok", "ignored": "campos ausentes"}

    # Precisa do Supabase configurado para registrar a resposta.
    if getattr(request.app.state, "supabase", None) is None:
        logger.warning("[webhook] Supabase indisponível — resposta não registrada")
        return {"status": "ok", "ignored": "supabase off"}

    try:
        instancia = await repo.get_instancia_by_token(token)
        if not instancia:
            logger.warning("[webhook] instância não encontrada para o token recebido")
            return {"status": "ok", "ignored": "instancia desconhecida"}

        tid = f"{phone}_{instancia['usuario_id']}_{instancia['id']}"
        redis = get_redis()
        raw = await redis.get(f"conv:{tid}")
        if not raw:
            logger.info("[webhook] sem contexto de disparo para %s (thread %s)", phone, tid)
            return {"status": "ok", "ignored": "sem contexto"}

        ctx = json.loads(raw)
        await repo.registrar_resposta_contato(
            campanha_id=ctx["campanha_id"],
            contato_id=ctx["contato_id"],
            resposta_texto=text,
        )
        await repo.incrementar_respostas(ctx["campanha_id"])
        logger.info(
            "[webhook] resposta registrada — campanha=%s contato=%s",
            ctx["campanha_id"], ctx["contato_id"],
        )

        # Salva a resposta na memória do grafo (não gera resposta automática).
        try:
            await request.app.state.graph.aupdate_state(
                {"configurable": {"thread_id": tid}},
                {"messages": [HumanMessage(content=text)]},
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("[webhook] falha ao atualizar memória do grafo: %s", e)

        return {"status": "ok", "registrado": True}
    except Exception as e:  # noqa: BLE001
        logger.exception("[webhook] erro ao processar resposta: %s", e)
        return {"status": "ok", "erro": True}
