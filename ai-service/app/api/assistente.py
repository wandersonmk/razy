"""Endpoints do assistente (uso interno — chamados pelo backend do Nuxt)."""

import logging
import re

from fastapi import APIRouter, Body, Header, HTTPException, Query

from app.config import get_settings
from app.db.redis import get_redis

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["assistente"])


def _verificar_token(authorization: str | None, x_internal_token: str | None) -> None:
    settings = get_settings()
    token = x_internal_token
    if not token and authorization:
        token = authorization.removeprefix("Bearer ").strip()
    if not token or token != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/assistente/pausas")
async def listar_pausas(
    usuario_id: str = Query(...),
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
):
    """Lista os contatos com atendimento pausado (chave pausa:{tel}_{usuario}_{instancia})
    e o tempo restante (TTL em segundos) de cada um, para o usuário informado."""
    _verificar_token(authorization, x_internal_token)
    redis = get_redis()
    pausas: list[dict] = []
    try:
        async for key in redis.scan_iter(match=f"pausa:*_{usuario_id}_*"):
            k = key.decode() if isinstance(key, (bytes, bytearray)) else key
            ttl = await redis.ttl(k)
            if ttl and ttl > 0:
                # k = "pausa:{telefone}_{usuario_id}_{instancia_id}"
                telefone = k[len("pausa:"):].split("_", 1)[0]
                pausas.append({"telefone": telefone, "segundos": int(ttl)})
    except Exception as e:  # noqa: BLE001
        logger.warning("[assistente] erro ao listar pausas: %s", e)
    return {"pausas": pausas}


@router.post("/assistente/pausas/remover")
async def remover_pausa(
    usuario_id: str = Body(..., embed=True),
    telefone: str = Body(..., embed=True),
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
):
    """Remove a pausa de um contato (despausar) — apaga a chave do Redis.
    Casa pelos últimos 11 dígitos do telefone (ignora o DDI 55)."""
    _verificar_token(authorization, x_internal_token)
    alvo = re.sub(r"\D", "", telefone or "")[-11:]
    if not alvo:
        return {"removidos": 0}
    redis = get_redis()
    removidos = 0
    try:
        async for key in redis.scan_iter(match=f"pausa:*_{usuario_id}_*"):
            k = key.decode() if isinstance(key, (bytes, bytearray)) else key
            tel = k[len("pausa:"):].split("_", 1)[0]
            if tel[-11:] == alvo:
                await redis.delete(k)
                removidos += 1
    except Exception as e:  # noqa: BLE001
        logger.warning("[assistente] erro ao remover pausa: %s", e)
    return {"removidos": removidos}
