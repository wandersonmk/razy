"""Cliente Redis assíncrono (memória / contexto de conversa)."""

from redis.asyncio import Redis

from app.config import get_settings

_client: Redis | None = None


async def init_redis() -> Redis:
    """Cria o cliente no startup e valida a conexão com um PING."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await _client.ping()
    return _client


async def close_redis() -> None:
    """Fecha o cliente graciosamente no shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_redis() -> Redis:
    """Retorna o cliente já inicializado (use dentro das rotas/serviços)."""
    if _client is None:
        raise RuntimeError("Cliente Redis não inicializado. Chame init_redis() no startup.")
    return _client
