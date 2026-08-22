"""Upload de mídia das conversas para o Supabase Storage (bucket privado
`conversas-midia`, criado na Fase 1 do canal por profissional).

O ai-service faz o upload com a service role key (bypassa RLS, é um serviço de
backend confiável — mesmo raciocínio de `repo.py`). A LEITURA no painel é via
signed URL, gerada pelo próprio Supabase JS no frontend a partir do
`storage_path` gravado em `midias_conversas` — este serviço nunca expõe URL
pública, só grava bytes.

Requer `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` no ambiente (opcionais: sem
elas, `upload_midia` retorna False e quem chama segue sem mídia anexada — nunca
trava o recebimento da mensagem por causa de storage).
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("uvicorn.error")

BUCKET = "conversas-midia"

# Pastas por tipo lógico dentro do bucket — {usuario_id}/{pasta}/{arquivo}.
# O usuario_id como PRIMEIRO segmento é o que a policy de Storage usa pra
# restringir a leitura só ao dono (ver migração
# canal_por_profissional_storage_policy) — nunca inverter essa ordem.
_KIND_TO_PASTA = {
    "audio": "audio",
    "image": "imagem",
    "sticker": "imagem",
    "document": "pdf",
    "video": "video",
}

# Foto de perfil do contato (cliente) — não é uma mensagem, é sincronizada à
# parte pro campo conversas.photo. Ver `services/conversas.sincronizar_foto_perfil`.
PASTA_FOTO_PERFIL = "foto_perfil"


def caminho_storage(*, usuario_id: str, kind: str, identificador: str, ext: str) -> str:
    """Monta o path dentro do bucket: {usuario_id}/{pasta}/{identificador}.{ext}.

    O prefixo `{usuario_id}/` é o que a policy de Storage usa para restringir
    leitura só ao dono (ver migração `canal_por_profissional_storage_policy`).
    """
    pasta = _KIND_TO_PASTA.get(kind, "pdf")
    ext_limpa = (ext or "bin").lstrip(".") or "bin"
    return f"{usuario_id}/{pasta}/{identificador}.{ext_limpa}"


def caminho_foto_perfil(*, usuario_id: str, conversa_id: str, ext: str) -> str:
    """Path da foto de perfil do contato: {usuario_id}/foto_perfil/{conversa_id}.{ext}."""
    ext_limpa = (ext or "jpg").lstrip(".") or "jpg"
    return f"{usuario_id}/{PASTA_FOTO_PERFIL}/{conversa_id}.{ext_limpa}"


async def upload_midia(*, path: str, conteudo: bytes, content_type: str) -> bool:
    """Envia os bytes pro bucket (upsert). Retorna True em sucesso.

    Nunca lança: qualquer falha (sem credenciais, rede, erro HTTP) vira False —
    quem chama deve seguir gravando a mensagem sem mídia anexada.
    """
    settings = get_settings()
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY):
        logger.info("[storage] SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY não configurados — upload pulado")
        return False

    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{BUCKET}/{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Content-Type": content_type or "application/octet-stream",
                    "x-upsert": "true",
                },
                content=conteudo,
            )
        if resp.status_code >= 400:
            logger.warning("[storage] upload falhou (%s) para %s: %s", resp.status_code, path, resp.text[:300])
            return False
        return True
    except Exception as e:
        logger.warning("[storage] erro no upload de %s: %s", path, e)
        return False
