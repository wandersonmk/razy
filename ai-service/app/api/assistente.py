"""Endpoints do assistente (uso interno — chamados pelo backend do Nuxt)."""

import logging
import re

from fastapi import APIRouter, Body, Header, HTTPException, Query

from app.config import get_settings
from app.db.redis import get_redis
from app.services import repo
from app.services.assistente import despausar_manual, pausar_atendimento, pausar_atendimento_manual
from app.services.telefone import so_digitos

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


# ── Pausa MANUAL por conversa (botão "Pausar" no painel de Conversas) ─────────
# Diferente de /assistente/pausas acima (que é por telefone, herdado do modelo
# de campanha): aqui o Nuxt já sabe exatamente qual (usuario_id, instancia_id,
# numero), então a chave é calculada direto — sem varredura no Redis.

@router.post("/conversas/pausar")
async def definir_pausa_manual(
    usuario_id: str = Body(..., embed=True),
    instancia_id: str = Body(..., embed=True),
    telefone: str = Body(..., embed=True),
    minutos: int = Body(..., embed=True),
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
):
    """Pausa manual (painel) — tem prioridade sobre a automática do webhook."""
    _verificar_token(authorization, x_internal_token)
    tel = so_digitos(telefone)
    if not tel:
        raise HTTPException(status_code=400, detail="telefone inválido")
    tid = f"{tel}_{usuario_id}_{instancia_id}"
    redis = get_redis()
    try:
        await pausar_atendimento_manual(redis, tid, minutos)
    except Exception as e:  # noqa: BLE001
        logger.warning("[assistente] erro ao definir pausa manual (%s): %s", tid, e)
        raise HTTPException(status_code=500, detail="falha ao pausar") from e
    return {"ok": True, "segundos": max(1, int(minutos)) * 60}


@router.post("/conversas/despausar")
async def remover_pausa_conversa(
    usuario_id: str = Body(..., embed=True),
    instancia_id: str = Body(..., embed=True),
    telefone: str = Body(..., embed=True),
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
):
    """Remove a pausa (manual ou automática) desta conversa específica."""
    _verificar_token(authorization, x_internal_token)
    tel = so_digitos(telefone)
    if not tel:
        raise HTTPException(status_code=400, detail="telefone inválido")
    tid = f"{tel}_{usuario_id}_{instancia_id}"
    redis = get_redis()
    try:
        await despausar_manual(redis, tid)
    except Exception as e:  # noqa: BLE001
        logger.warning("[assistente] erro ao despausar conversa (%s): %s", tid, e)
        raise HTTPException(status_code=500, detail="falha ao despausar") from e
    return {"ok": True}


# ── Pausa AUTOMÁTICA disparada pelo composer do painel (dono manda mensagem) ──
# Mesmo mecanismo que já pausa quando o profissional responde pelo celular
# (ver api/webhook.py, bloco "Mensagem ENVIADA (fromMe)"): reusa
# pausar_atendimento (respeita pausa manual ativa, nunca a derruba) e
# marcar_pausa_conversa (espelha em `conversas` pro badge). A diferença é só a
# ORIGEM do gatilho — de um evento de webhook para uma chamada do Nuxt depois
# de o dono mandar algo pelo composer.

@router.post("/conversas/pausar-automatica")
async def definir_pausa_automatica(
    usuario_id: str = Body(..., embed=True),
    instancia_id: str = Body(..., embed=True),
    telefone: str = Body(..., embed=True),
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
):
    """Pausa automática — mesma config (pausa_ativa/pausa_minutos) que rege a
    pausa quando o profissional responde pelo celular. Se o dono desligou a
    pausa automática para este canal, este endpoint não faz nada — mandar pelo
    app não pode pausar algo que mandar pelo celular não pausaria."""
    _verificar_token(authorization, x_internal_token)
    tel = so_digitos(telefone)
    if not tel:
        raise HTTPException(status_code=400, detail="telefone inválido")

    cfg = await repo.resolver_pausa_config(instancia_id=instancia_id, usuario_id=usuario_id)
    if not cfg or not cfg.get("pausa_ativa"):
        return {"ok": True, "pausado": False}

    minutos = int(cfg.get("pausa_minutos") or 30)
    tid = f"{tel}_{usuario_id}_{instancia_id}"
    redis = get_redis()
    try:
        await pausar_atendimento(redis, tid, minutos)
        await repo.marcar_pausa_conversa(
            usuario_id=usuario_id, instancia_id=instancia_id, numero=tel, minutos=minutos,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[assistente] erro ao pausar automaticamente (%s): %s", tid, e)
        raise HTTPException(status_code=500, detail="falha ao pausar") from e
    return {"ok": True, "pausado": True, "segundos": minutos * 60}
