"""Construção do grafo LangGraph.

Grafo mínimo de geração de mensagem: 1 nó de LLM que escreve uma mensagem de
WhatsApp personalizada a partir da observação do contato. O checkpointer
(Postgres) persiste o histórico por `thread_id` (telefone_empresa_instancia),
dando memória de conversa para quando o cliente responder.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.config import get_settings

# Nome do único nó do grafo. Usado também ao aplicar updates manuais de memória
# (aupdate_state): com mais de um "step" na thread, o LangGraph não consegue
# inferir o nó de origem e levanta "Ambiguous update, specify as_node" — então
# sempre passamos as_node=LLM_NODE explicitamente.
LLM_NODE = "llm"

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


def _build_llm(api_key: str | None = None) -> ChatOpenAI:
    settings = get_settings()
    key = api_key or settings.OPENAI_API_KEY
    if not key:
        raise ValueError(
            "Chave OpenAI não configurada. Acesse Configurações → Integrações no painel e informe sua chave da API."
        )
    return ChatOpenAI(
        api_key=key,
        model="gpt-4.1-mini",
        temperature=0.7,
    )


async def _llm_node(state: GraphState, config: RunnableConfig) -> dict:
    """Gera a resposta do LLM.

    Aceita `api_key` opcional via config["configurable"]["api_key"] — permite
    que cada usuário use sua própria chave OpenAI configurada no painel.
    """
    api_key: str | None = (config.get("configurable") or {}).get("api_key")
    llm = _build_llm(api_key)
    msgs = list(state["messages"])
    if not any(isinstance(m, SystemMessage) for m in msgs):
        msgs = [SystemMessage(content=SYSTEM_PROMPT), *msgs]
    response = await llm.ainvoke(msgs)
    return {"messages": [response]}


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Compila o StateGraph usando o checkpointer Postgres."""
    graph = StateGraph(GraphState)
    graph.add_node(LLM_NODE, _llm_node)
    graph.add_edge(START, LLM_NODE)
    graph.add_edge(LLM_NODE, END)
    # TODO: registrar nós de negócio, tools e arestas condicionais aqui.
    return graph.compile(checkpointer=checkpointer)


async def gerar_mensagem(graph, *, thread_id: str, nome: str, observacao: str, api_key: str | None = None) -> str:
    """Invoca o grafo para gerar a mensagem inicial de um contato.

    Usa `thread_id` para persistir o contexto (memória) dessa conversa.
    """
    prompt = (
        f"Cliente: {nome or 'cliente'}\n"
        f"Observação/contexto sobre o cliente: {observacao or '(sem observação)'}\n\n"
        "Escreva a mensagem inicial de WhatsApp para este cliente."
    )
    cfg: dict = {"configurable": {"thread_id": thread_id}}
    if api_key:
        cfg["configurable"]["api_key"] = api_key
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=prompt)]},
        config=cfg,
    )
    last = result["messages"][-1]
    return (last.content or "").strip()


async def gerar_followup(
    graph, *, thread_id: str, nome: str, observacao: str, etapa: int, api_key: str | None = None
) -> str:
    """Gera uma mensagem de FOLLOW-UP usando o contexto acumulado da conversa.

    O `thread_id` é o mesmo do disparo original, então o histórico (mensagem inicial
    + mensagens manuais já registradas + respostas do cliente) está disponível para a IA.
    """
    prompt = (
        f"Cliente: {nome or 'cliente'}\n"
        f"Observação/contexto: {observacao or '(sem observação)'}\n\n"
        f"Este é o follow-up nº {etapa}. O cliente ainda NÃO respondeu às mensagens anteriores "
        "(veja o histórico acima). Escreva uma nova mensagem curta de follow-up, cordial e natural, "
        "retomando levemente o assunto da conversa anterior, sem ser insistente nem repetir o que já foi dito. "
        "Responda apenas com o texto da mensagem."
    )
    cfg: dict = {"configurable": {"thread_id": thread_id}}
    if api_key:
        cfg["configurable"]["api_key"] = api_key
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=prompt)]},
        config=cfg,
    )
    last = result["messages"][-1]
    return (last.content or "").strip()


async def registrar_no_contexto(graph, *, thread_id: str, texto: str) -> None:
    """Anexa uma mensagem ENVIADA (manual) ao estado da thread, como se fosse do assistente.

    Garante que etapas seguintes (IA) tenham o contexto completo mesmo quando a etapa
    anterior usou mensagem manual. Idempotência não é garantida — chamar uma vez por envio.
    """
    await graph.aupdate_state(
        {"configurable": {"thread_id": thread_id}},
        {"messages": [AIMessage(content=texto)]},
        as_node=LLM_NODE,
    )
