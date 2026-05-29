"""Construção do grafo LangGraph.

ESQUELETO: por enquanto há apenas 1 nó de LLM (placeholder).
Adicione aqui depois: nós de negócio, tools, roteamento condicional, etc.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.config import get_settings


class GraphState(TypedDict):
    """Estado do grafo. Expanda conforme a necessidade do fluxo."""

    messages: Annotated[list[BaseMessage], add_messages]


def _build_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model="gpt-4o-mini",
        temperature=0,
    )


async def _llm_node(state: GraphState) -> dict:
    """Nó único de placeholder: chama o LLM com o histórico de mensagens."""
    llm = _build_llm()
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Compila o StateGraph mínimo usando o checkpointer Postgres.

    Args:
        checkpointer: persistência de estado (criada no lifespan em app/main.py).
    """
    graph = StateGraph(GraphState)

    graph.add_node("llm", _llm_node)
    graph.add_edge(START, "llm")
    graph.add_edge("llm", END)

    # TODO: registrar nós de negócio, tools e arestas condicionais aqui.

    return graph.compile(checkpointer=checkpointer)
