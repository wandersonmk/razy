"""Webhook de recebimento da UAzAPI (mensagens recebidas / respostas do cliente).

ESQUELETO: por enquanto apenas registra o payload bruto nos logs, para
descobrirmos o formato exato que a UAzAPI envia quando o cliente responde.
A lógica de negócio (casar a conversa por telefone_empresa_instancia,
gravar resposta_texto e incrementar total_respostas) entra na próxima fase,
quando tivermos a connection string do Supabase.
"""

import logging
from typing import Any

from fastapi import APIRouter, Request

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["webhook"])


def _pick(d: Any, *keys: str) -> Any:
    """Retorna o primeiro campo não-vazio entre os nomes possíveis."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


@router.post("/webhook/uazapi")
async def webhook_uazapi(request: Request):
    # Aceita qualquer corpo — ainda não conhecemos o formato exato da UAzAPI.
    try:
        payload = await request.json()
    except Exception:
        raw = (await request.body()).decode("utf-8", "ignore")
        logger.warning("[webhook] corpo não-JSON: %s", raw[:2000])
        return {"status": "ignored", "reason": "non-json"}

    # Loga o payload inteiro para inspecionarmos o formato real nos logs do EasyPanel.
    logger.info("[webhook] payload recebido: %s", payload)

    # Extração defensiva dos campos mais prováveis (ajustaremos com o formato real).
    data = payload.get("message") or payload.get("data") or payload
    from_me = bool(_pick(data, "fromMe", "fromme") or False)
    number = _pick(data, "sender_pn", "sender", "chatid", "number", "phone")
    text = _pick(data, "text", "body", "message", "conteudo")
    instance = _pick(payload, "instance", "owner", "instancia") or _pick(data, "instance", "owner")

    if from_me:
        logger.info("[webhook] ignorando mensagem enviada por nós (fromMe)")
        return {"status": "ok", "ignored": "fromMe"}

    logger.info(
        "[webhook] RESPOSTA do cliente — number=%s instance=%s text=%r",
        number, instance, text,
    )

    # TODO (próxima fase — requer Supabase):
    #   1. thread_id = f"{telefone}_{empresa_id}_{instancia_id}" → recuperar contexto (Redis/checkpointer)
    #   2. localizar o disparo aberto desse contato → gravar resposta_texto + respondido_em
    #   3. incrementar campanhas.total_respostas
    return {"status": "ok"}
