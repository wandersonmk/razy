# Razy AI Service

Esqueleto de um serviço de IA em Python (FastAPI + LangChain + LangGraph) para os
disparos do Razy. Apenas a estrutura base — sem tools, nós de negócio ou integrações.

## Stack

- Python 3.13 · FastAPI · Uvicorn
- LangChain · LangGraph (checkpointer no Postgres)
- Pydantic v2 / pydantic-settings
- Redis (memória/contexto) · Postgres (asyncpg + checkpointer)

## Estrutura

```
ai-service/
├── app/
│   ├── main.py          # FastAPI + lifespan (startup/shutdown)
│   ├── config.py        # Settings (env vars)
│   ├── api/health.py    # GET /healthz
│   ├── db/postgres.py   # pool asyncpg
│   ├── db/redis.py      # cliente Redis
│   └── graph/build.py   # StateGraph mínimo (1 nó de LLM, placeholder)
├── Dockerfile
├── pyproject.toml
└── .env.example
```

## Rodar localmente

As variáveis vêm do **`.env` da raiz do projeto** (o mesmo do app Nuxt) — preencha
`OPENAI_API_KEY`, `POSTGRES_URL`, `REDIS_URL` e `INTERNAL_TOKEN` lá.

```bash
cd ai-service
uv pip install --system -r pyproject.toml
uvicorn app.main:app --reload --port 8000
# valida:
curl http://127.0.0.1:8000/healthz   # {"status":"ok"}
```

> O startup exige Postgres e Redis acessíveis (o checkpointer roda `setup()` no Postgres).

## Docker

```bash
cd ai-service
docker build -t razy-ai-service .
docker run --rm -p 8000:8000 --env-file .env razy-ai-service
```

## Variáveis de ambiente

| Variável         | Descrição                                  |
|------------------|--------------------------------------------|
| `OPENAI_API_KEY` | Chave da OpenAI                            |
| `POSTGRES_URL`   | DSN do Postgres (app + checkpointer)       |
| `REDIS_URL`      | URL do Redis                               |
| `INTERNAL_TOKEN` | Token de chamadas internas (uso futuro)    |
