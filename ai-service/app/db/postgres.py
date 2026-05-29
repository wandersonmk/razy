"""Pool de conexões asyncpg (uso geral da aplicação).

Obs.: o checkpointer do LangGraph mantém a própria conexão Postgres
(via psycopg) — ver app/main.py. Este pool é para queries diretas da app.
"""

import asyncpg

from app.config import get_settings

_pool: asyncpg.Pool | None = None


async def init_postgres() -> asyncpg.Pool:
    """Cria o pool no startup (idempotente)."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.POSTGRES_URL,
            min_size=1,
            max_size=10,
        )
    return _pool


async def close_postgres() -> None:
    """Fecha o pool graciosamente no shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Retorna o pool já inicializado (use dentro das rotas/serviços)."""
    if _pool is None:
        raise RuntimeError("Pool Postgres não inicializado. Chame init_postgres() no startup.")
    return _pool
