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
    # Opcional: se não definida no .env, cada usuário deve configurar a própria
    # chave pelo painel (Configurações → Integrações). O ai-service falha com
    # mensagem clara se nenhuma chave estiver disponível no momento do disparo.
    OPENAI_API_KEY: str | None = None
    POSTGRES_URL: str
    REDIS_URL: str

    # Postgres do Supabase (dados de negócio: contatos, campanhas, disparos).
    # Opcional para o serviço subir; obrigatório para o disparo/IA funcionar.
    SUPABASE_DB_URL: str | None = None

    # API REST/Storage do Supabase (upload de mídia das conversas — canal por
    # profissional). Opcionais: sem elas, a mídia simplesmente não é persistida
    # no Storage (a mensagem é gravada mesmo assim, só sem anexo).
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # Base da UAzAPI (servidor onde as instâncias vivem).
    UAZAPI_URL: str = "https://razycorretora.uazapi.com"

    # Token para autenticar chamadas internas (uso futuro nas rotas protegidas)
    INTERNAL_TOKEN: str

    # Janela (segundos) para agrupar mensagens em rajada do mesmo contato numa
    # única resposta da IA — ver `enfileirar_mensagem` em services/assistente.py.
    # 0 desliga o agrupamento (a IA responde cada mensagem na hora, como antes).
    IA_JANELA_RAJADA_S: int = 6


@lru_cache
def get_settings() -> Settings:
    """Instância única (cacheada) das configurações."""
    return Settings()  # type: ignore[call-arg]
