"""Aplicação FastAPI.

Lifespan:
  - startup: abre o pool Postgres, o cliente Redis e o checkpointer do LangGraph,
    e compila o grafo (placeholder).
  - shutdown: fecha tudo graciosamente (ordem inversa, via AsyncExitStack).
"""

import asyncio
import logging
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api.campanhas import router as campanhas_router
from app.api.health import router as health_router
from app.api.webhook import router as webhook_router
from app.config import get_settings
from app.db.postgres import close_postgres, init_postgres
from app.db.redis import close_redis, init_redis
from app.db.supabase import close_supabase, init_supabase
from app.graph.build import build_graph
from app.services import repo
from app.services.orquestrador import agendar_disparo

logger = logging.getLogger("uvicorn.error")


async def _cancelar_task(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _scheduler_loop(app: FastAPI) -> None:
    """A cada 60s, inicia campanhas agendadas cujo horário já chegou."""
    while True:
        try:
            await asyncio.sleep(60)
            if getattr(app.state, "supabase", None) is None:
                continue
            for c in await repo.get_campanhas_agendadas_vencidas():
                logger.info("[scheduler] iniciando campanha agendada %s", c["id"])
                agendar_disparo(app, c["id"])
        except asyncio.CancelledError:
            break
        except Exception as e:  # noqa: BLE001
            logger.exception("[scheduler] erro no loop: %s", e)

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

        # Postgres do Supabase (dados de negócio) — opcional no boot
        app.state.supabase = await init_supabase()
        stack.push_async_callback(close_supabase)
        if app.state.supabase is None:
            logger.warning("SUPABASE_DB_URL não definido — disparo/IA indisponível até configurar.")
        else:
            logger.info("Conectado ao Postgres do Supabase (dados de negócio).")

        # Checkpointer do LangGraph (estado persistido no Postgres)
        # TODO: para alta concorrência, trocar por AsyncConnectionPool dedicado.
        checkpointer = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(settings.POSTGRES_URL)
        )
        await checkpointer.setup()  # cria as tabelas do checkpointer se necessário
        app.state.checkpointer = checkpointer

        # Grafo compilado (placeholder: 1 nó de LLM)
        app.state.graph = build_graph(checkpointer)

        # Scheduler de campanhas agendadas (inicia as vencidas a cada 60s)
        scheduler_task = asyncio.create_task(_scheduler_loop(app))
        stack.push_async_callback(_cancelar_task, scheduler_task)

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
app.include_router(webhook_router)    # POST /webhook/uazapi (resposta do cliente)
app.include_router(campanhas_router)  # POST /campanhas/{id}/iniciar (disparo IA/manual)
