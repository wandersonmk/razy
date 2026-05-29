"""Aplicação FastAPI.

Lifespan:
  - startup: abre o pool Postgres, o cliente Redis e o checkpointer do LangGraph,
    e compila o grafo (placeholder).
  - shutdown: fecha tudo graciosamente (ordem inversa, via AsyncExitStack).
"""

from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api.health import router as health_router
from app.api.webhook import router as webhook_router
from app.config import get_settings
from app.db.postgres import close_postgres, init_postgres
from app.db.redis import close_redis, init_redis
from app.graph.build import build_graph

# Origens liberadas para o front (Nuxt na Vercel + dev local).
ALLOWED_ORIGINS = [
    "https://razy.vercel.app",
    "http://localhost:3000",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    async with AsyncExitStack() as stack:
        # Postgres (pool de uso geral da aplicação)
        app.state.pg_pool = await init_postgres()
        stack.push_async_callback(close_postgres)

        # Redis (memória / contexto de conversa)
        app.state.redis = await init_redis()
        stack.push_async_callback(close_redis)

        # Checkpointer do LangGraph (estado persistido no Postgres)
        # TODO: para alta concorrência, trocar por AsyncConnectionPool dedicado.
        checkpointer = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(settings.POSTGRES_URL)
        )
        await checkpointer.setup()  # cria as tabelas do checkpointer se necessário
        app.state.checkpointer = checkpointer

        # Grafo compilado (placeholder: 1 nó de LLM)
        app.state.graph = build_graph(checkpointer)

        yield
        # AsyncExitStack fecha checkpointer -> redis -> postgres ao sair.


app = FastAPI(title="Razy AI Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(webhook_router)  # POST /webhook/uazapi (resposta do cliente)
