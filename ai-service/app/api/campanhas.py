"""Endpoints de campanha (chamados pelo backend do Nuxt, não pelo navegador)."""

import logging

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import get_settings
from app.services.orquestrador import agendar_disparo

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["campanhas"])


def _verificar_token(authorization: str | None, x_internal_token: str | None) -> None:
    settings = get_settings()
    token = x_internal_token
    if not token and authorization:
        token = authorization.removeprefix("Bearer ").strip()
    if not token or token != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.post("/campanhas/{campanha_id}/iniciar")
async def iniciar_campanha(
    campanha_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
):
    _verificar_token(authorization, x_internal_token)

    if getattr(request.app.state, "supabase", None) is None:
        raise HTTPException(status_code=503, detail="Supabase não configurado no ai-service")

    agendar_disparo(request.app, campanha_id)
    logger.info("[campanhas] disparo agendado para %s", campanha_id)
    return {"status": "iniciado", "campanha_id": campanha_id}
