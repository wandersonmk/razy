"""Construção do grafo LangGraph.

Grafo mínimo de geração de mensagem: 1 nó de LLM que escreve uma mensagem de
WhatsApp personalizada a partir da observação do contato. O checkpointer
(Postgres) persiste o histórico por `thread_id` (telefone_empresa_instancia),
dando memória de conversa para quando o cliente responder.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.config import get_settings

SYSTEM_PROMPT = (
    "Você é um assistente de relacionamento que escreve mensagens de WhatsApp para clientes. "
    "Escreva UMA única mensagem curta (1 a 3 frases), cordial e natural, em português do Brasil, "
    "personalizada com base no contexto/observação fornecido sobre o cliente. "
    "Não use aspas, não adicione explicações nem assinaturas: responda apenas com o texto da "
    "mensagem que será enviada ao cliente."
)


class GraphState(TypedDict):
    """Estado do grafo. Expanda conforme a necessidade do fluxo."""

    messages: Annotated[list[BaseMessage], add_messages]


def _build_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model="gpt-4o-mini",
        temperature=0.7,
    )


async def _llm_node(state: GraphState) -> dict:
    """Gera a resposta do LLM, garantindo o system prompt no início do contexto."""
    llm = _build_llm()
    msgs = list(state["messages"])
    if not any(isinstance(m, SystemMessage) for m in msgs):
        msgs = [SystemMessage(content=SYSTEM_PROMPT), *msgs]
    response = await llm.ainvoke(msgs)
    return {"messages": [response]}


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Compila o StateGraph usando o checkpointer Postgres."""
    graph = StateGraph(GraphState)
    graph.add_node("llm", _llm_node)
    graph.add_edge(START, "llm")
    graph.add_edge("llm", END)
    # TODO: registrar nós de negócio, tools e arestas condicionais aqui.
    return graph.compile(checkpointer=checkpointer)


async def gerar_mensagem(graph, *, thread_id: str, nome: str, observacao: str) -> str:
    """Invoca o grafo para gerar a mensagem inicial de um contato.

    Usa `thread_id` para persistir o contexto (memória) dessa conversa.
    """
    prompt = (
        f"Cliente: {nome or 'cliente'}\n"
        f"Observação/contexto sobre o cliente: {observacao or '(sem observação)'}\n\n"
        "Escreva a mensagem inicial de WhatsApp para este cliente."
    )
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=prompt)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    last = result["messages"][-1]
    return (last.content or "").strip()
