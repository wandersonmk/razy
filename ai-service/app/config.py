"""Configuração da aplicação via variáveis de ambiente (Pydantic v2)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env compartilhado na raiz do projeto (o mesmo do app Nuxt).
# Em produção (EasyPanel) as variáveis vêm do painel; se o arquivo não existir,
# o pydantic-settings simplesmente ignora e usa as variáveis do ambiente.
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Lê as variáveis de ambiente. Falha cedo se algo obrigatório faltar."""

    model_config = SettingsConfigDict(
        env_file=_ROOT_ENV,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Credenciais / conexões
    OPENAI_API_KEY: str
    POSTGRES_URL: str
    REDIS_URL: str

    # Token para autenticar chamadas internas (uso futuro nas rotas protegidas)
    INTERNAL_TOKEN: str


@lru_cache
def get_settings() -> Settings:
    """Instância única (cacheada) das configurações."""
    return Settings()  # type: ignore[call-arg]
