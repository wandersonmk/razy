"""Configuração da aplicação via variáveis de ambiente (Pydantic v2)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env compartilhado na raiz do projeto (o mesmo do app Nuxt).
# Em produção (EasyPanel) as variáveis vêm do painel; se o arquivo não existir,
# o pydantic-settings simplesmente ignora e usa as variáveis do ambiente.
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"

# Modelo da OpenAI usado em TODO o serviço: atendimento, disparo/follow-up,
# leitura de imagem e Analista. Um lugar só, para nunca ficarem divergentes.
#
# gpt-6-luna substitui o gpt-4.1-mini, que a OpenAI desliga em 14/01/2027 — é o
# substituto indicado na página oficial de deprecations. Também é 4x mais
# barato na entrada (US$ 0,10 contra 0,40 por milhão de tokens).
#
# Ele é um modelo de RACIOCÍNIO. Com effort "none" responde direto, rápido como
# o anterior, e é o único modo em que o Chat Completions aceita function calling
# (o Analista usa tools). Por isso nenhuma chamada manda `temperature`: a doc só
# garante os parâmetros de amostragem com effort "none", e há relato de saída
# estruturada quebrada quando eles vão junto. Se um dia subir o effort, não basta
# trocar aqui: confira as chamadas com tools (Analista) e o `max_completion_tokens`
# da visão, que passaria a incluir os tokens de raciocínio.
MODELO_OPENAI = "gpt-6-luna"
ESFORCO_RACIOCINIO = "none"


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
    #
    # 8s vem das 33 duplicatas medidas no banco em 26-27/08: o intervalo entre as
    # duas mensagens do cliente teve mediana 3,4s, p90 5,6s e MÁXIMO 7,3s — 8s
    # cobre todos os casos observados. 6s cobriria 94%. Cada segundo aqui é
    # latência somada a TODA resposta, então não vale subir sem dado novo.
    IA_JANELA_RAJADA_S: int = 8


@lru_cache
def get_settings() -> Settings:
    """Instância única (cacheada) das configurações."""
    return Settings()  # type: ignore[call-arg]
