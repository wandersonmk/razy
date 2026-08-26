"""Endpoints do Analista de Atendimento (uso interno — chamados pelo backend Nuxt).

`usuario_id` chega do Nuxt, que já validou o JWT do Supabase. Nunca aceite esse
campo vindo do navegador sem essa validação: é ele que separa os dados de uma
empresa dos da outra (o ai-service conecta como `postgres` e bypassa RLS).
"""

import logging

from fastapi import APIRouter, Body, Header, HTTPException

from app.config import get_settings
from app.services import analista, repo
from app.services import analista_consultas as consultas

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["analista"])


def _verificar_token(authorization: str | None, x_internal_token: str | None) -> None:
    settings = get_settings()
    token = x_internal_token
    if not token and authorization:
        token = authorization.removeprefix("Bearer ").strip()
    if not token or token != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/analista/resumo")
async def resumo(
    usuario_id: str,
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
):
    """Números da operação mostrados assim que o painel abre (antes de perguntar).

    Não passa por LLM de propósito: é consulta pura, precisa ser instantânea e
    não pode gastar token a cada vez que alguém abre o painel.
    """
    _verificar_token(authorization, x_internal_token)
    try:
        return await consultas.resumo_operacao(usuario_id=usuario_id)
    except Exception as e:
        logger.warning("[analista] falha no resumo de %s: %s", usuario_id, e)
        raise HTTPException(status_code=503, detail="não foi possível carregar o resumo")


@router.post("/analista/perguntar")
async def perguntar(
    usuario_id: str = Body(...),
    pergunta: str = Body(...),
    historico: list[dict] | None = Body(default=None),
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
):
    """Responde uma pergunta sobre os atendimentos.

    Usa a chave OpenAI do PAINEL do usuário (Configurações → Integrações), com
    fallback para a do .env — mesmo critério do resto do serviço.
    """
    _verificar_token(authorization, x_internal_token)

    texto = (pergunta or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="pergunta vazia")
    if len(texto) > 2000:
        raise HTTPException(status_code=400, detail="pergunta muito longa")

    api_key = await repo.get_openai_key(usuario_id) or get_settings().OPENAI_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Configure sua chave da OpenAI em Configurações → Integrações para usar o analista.",
        )

    try:
        return await analista.perguntar(
            usuario_id=usuario_id, pergunta=texto, api_key=api_key, historico=historico,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
