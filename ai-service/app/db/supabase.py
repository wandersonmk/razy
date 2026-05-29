"""Pool asyncpg para o Postgres do Supabase (dados de negócio).

Separado do pool do checkpointer (app/db/postgres.py): aqui ficam as queries
de contatos, campanhas e disparos. Conecta via session pooler (IPv4) do Supabase.
"""

import asyncpg

from app.config import get_settings

_pool: asyncpg.Pool | None = None


async def init_supabase() -> asyncpg.Pool | None:
    """Cria o pool no startup. Retorna None se SUPABASE_DB_URL não estiver definido."""
    global _pool
    settings = get_settings()
    if not settings.SUPABASE_DB_URL:
        return None
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.SUPABASE_DB_URL,
            min_size=1,
            max_size=10,
            # Compatibilidade com o pooler do Supabase (Supavisor).
            statement_cache_size=0,
        )
    return _pool


async def close_supabase() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_supabase_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError(
            "Pool do Supabase não inicializado. Defina SUPABASE_DB_URL e reinicie o serviço."
        )
    return _pool
