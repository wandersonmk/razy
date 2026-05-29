"""Assistente de IA — primeiro atendimento ao cliente que responde.

Quando o cliente responde a um disparo (ou manda mensagem), o assistente:
  1. Responde no WhatsApp usando as instruções e dados da empresa configurados.
  2. Coleta informações do cliente (interesse, dados de contato, etc.).
  3. Quando a coleta está completa, encaminha o resumo para o número do atendente.

Mantém o contexto da conversa no checkpointer do LangGraph (mesma thread do
disparo original), então o histórico (mensagem inicial + follow-ups + respostas)
fica disponível. Áudios do cliente são transcritos via OpenAI (whisper) antes.
"""

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn.error")


class RespostaAssistente(BaseModel):
    """Saída estruturada do assistente."""
    resposta: str = Field(description="Mensagem a ser enviada ao cliente no WhatsApp, em português do Brasil.")
    coleta_completa: bool = Field(
        default=False,
        description="true quando já coletou os dados necessários e o cliente deve ser encaminhado a um atendente humano.",
    )
    resumo_atendimento: str | None = Field(
        default=None,
        description="Quando coleta_completa=true: resumo do atendimento e todos os dados coletados, para enviar ao atendente.",
    )


def montar_system_prompt(cfg: dict) -> str:
    """Monta o prompt do sistema a partir da configuração do assistente."""
    empresa = (cfg.get("empresa_nome") or "").strip()
    info = (cfg.get("empresa_info") or "").strip()
    horario = (cfg.get("horario_funcionamento") or "").strip()
    instrucao = (cfg.get("instrucao") or "").strip()
    tem_atendente = bool((cfg.get("atendente_telefone") or "").strip())

    partes = [
        "Você é o assistente virtual de atendimento de uma empresa, conversando com um cliente pelo WhatsApp.",
        "Responda sempre em português do Brasil, de forma cordial, objetiva e natural (mensagens curtas, como no WhatsApp).",
    ]
    if empresa:
        partes.append(f"Empresa: {empresa}.")
    if info:
        partes.append(f"Informações da empresa e dos produtos/planos:\n{info}")
    if horario:
        partes.append(f"Horário de funcionamento: {horario}.")
    if instrucao:
        partes.append(f"Instruções específicas do dono da empresa (siga à risca):\n{instrucao}")

    partes.append(
        "Seu objetivo é dar o primeiro atendimento: tirar dúvidas, passar informações sobre os planos "
        "e COLETAR os dados do cliente (nome, interesse, melhor horário de contato e o que mais for relevante)."
    )
    if tem_atendente:
        partes.append(
            "Quando tiver coletado os dados essenciais e o cliente demonstrar interesse real em falar com um "
            "atendente humano (ou a coleta estiver completa), defina coleta_completa=true e escreva em "
            "resumo_atendimento um resumo com TODOS os dados coletados. Nesse caso, na 'resposta' avise o "
            "cliente, de forma calorosa, que um atendente dará continuidade em instantes. "
            "Enquanto a coleta não estiver completa, mantenha coleta_completa=false."
        )
    else:
        partes.append("Mantenha sempre coleta_completa=false (não há atendente configurado).")

    return "\n\n".join(partes)


async def responder_como_assistente(
    graph,
    *,
    thread_id: str,
    cfg: dict,
    texto_cliente: str,
    api_key: str,
) -> RespostaAssistente:
    """Gera a resposta do assistente usando o histórico da thread + saída estruturada.

    Lê o histórico pelo checkpointer (mesma thread do disparo), chama o LLM com
    structured output e grava a troca (cliente + assistente) de volta na thread.
    """
    cfg_run = {"configurable": {"thread_id": thread_id}}

    # Histórico acumulado da conversa (mensagem inicial, follow-ups, respostas anteriores).
    historico: list = []
    try:
        snap = await graph.aget_state(cfg_run)
        if snap and snap.values:
            historico = list(snap.values.get("messages", []))
    except Exception as e:
        logger.warning("[assistente] não foi possível ler histórico (%s): %s", thread_id, e)

    system_prompt = montar_system_prompt(cfg)
    llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini", temperature=0.5)
    estruturado = llm.with_structured_output(RespostaAssistente)

    mensagens = [SystemMessage(content=system_prompt), *historico, HumanMessage(content=texto_cliente)]

    try:
        resultado: RespostaAssistente = await estruturado.ainvoke(mensagens)
    except Exception as e:
        logger.exception("[assistente] erro ao gerar resposta: %s", e)
        # Fallback: resposta neutra, sem encaminhar.
        resultado = RespostaAssistente(
            resposta="Recebi sua mensagem! Em breve retornamos com mais informações. 🙏",
            coleta_completa=False,
        )

    # Grava a troca na thread (cliente + assistente) para manter o contexto.
    try:
        await graph.aupdate_state(
            cfg_run,
            {"messages": [HumanMessage(content=texto_cliente), AIMessage(content=resultado.resposta)]},
        )
    except Exception as e:
        logger.warning("[assistente] falha ao gravar contexto (%s): %s", thread_id, e)

    return resultado


# ── Transcrição de áudio (OpenAI Whisper) ────────────────────────────────────

async def transcrever_audio(*, audio_bytes: bytes, filename: str, api_key: str) -> str:
    """Transcreve um áudio (bytes) usando a API de transcrição da OpenAI."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        resp = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename or "audio.ogg", audio_bytes),
        )
        texto = (getattr(resp, "text", "") or "").strip()
        logger.info("[assistente] áudio transcrito (%d chars)", len(texto))
        return texto
    except Exception as e:
        logger.exception("[assistente] erro ao transcrever áudio: %s", e)
        return ""
