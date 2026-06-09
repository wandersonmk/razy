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
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.graph.build import LLM_NODE

logger = logging.getLogger("uvicorn.error")


# ── Validação determinística de CPF/CNPJ ─────────────────────────────────────

def _digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def validar_cpf(cpf: str) -> bool:
    cpf = _digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[n]) * ((i + 1) - n) for n in range(i))
        d = (soma * 10) % 11
        d = 0 if d == 10 else d
        if d != int(cpf[i]):
            return False
    return True


def validar_cnpj(cnpj: str) -> bool:
    cnpj = _digitos(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    for pesos, i in ((pesos1, 12), (pesos2, 13)):
        soma = sum(int(cnpj[n]) * pesos[n] for n in range(i))
        d = soma % 11
        d = 0 if d < 2 else 11 - d
        if d != int(cnpj[i]):
            return False
    return True


def validar_documentos_no_texto(texto: str) -> str:
    """Procura sequências de 11 (CPF) ou 14 (CNPJ) dígitos na mensagem do cliente
    e valida os dígitos verificadores. Retorna uma nota objetiva para a IA usar."""
    notas: list[str] = []
    for m in re.finditer(r"\d[\d.\-/ ]{9,17}\d", texto or ""):
        bruto = m.group().strip()
        d = _digitos(bruto)
        if len(d) == 11:
            notas.append(f"CPF '{bruto}': {'VÁLIDO' if validar_cpf(d) else 'INVÁLIDO (dígitos verificadores não conferem)'}.")
        elif len(d) == 14:
            notas.append(f"CNPJ '{bruto}': {'VÁLIDO' if validar_cnpj(d) else 'INVÁLIDO (dígitos verificadores não conferem)'}.")
    return " ".join(notas)


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
    sem_interesse: bool = Field(
        default=False,
        description=(
            "true SOMENTE quando o cliente deixar CLARO que NÃO tem interesse na oferta: "
            "diz que já tem/usa o produto ou um concorrente (ex.: 'já tenho Bradesco'), "
            "recusa explicitamente, pede para não receber mais mensagens, ou responde de forma "
            "claramente negativa ao assunto. NÃO marque true por dúvida, objeção contornável, "
            "indisponibilidade momentânea ('agora não posso') ou silêncio."
        ),
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
    partes.append(
        "REGRAS IMPORTANTES DE COLETA (siga rigorosamente):\n"
        "1. NUNCA invente, adivinhe ou deduza dados. Registre apenas o que o cliente informou EXPLICITAMENTE.\n"
        "2. Cada dado precisa ser COERENTE com o campo perguntado. Exemplos: 'idade' deve ser um número de "
        "anos (ex.: 35); um nome NÃO é idade; um valor em reais NÃO é idade. Se a resposta do cliente não "
        "corresponder ao que foi perguntado, NÃO registre — reconheça o que já sabe e pergunte de novo com "
        "gentileza. Ex.: 'Perfeito, já anotei seu nome como Wanderson. Agora, qual a sua idade, por favor?'\n"
        "3. CPF e CNPJ: use SEMPRE o resultado da validação automática fornecida pelo sistema (quando houver). "
        "Se for INVÁLIDO, avise o cliente educadamente e peça o número correto; não registre documentos inválidos.\n"
        "4. Se o cliente fizer uma pergunta ou mudar de assunto no meio da coleta, responda a dúvida dele "
        "e, na sequência, retome de forma natural o dado que ainda falta coletar — sem reiniciar do zero.\n"
        "5. O resumo enviado ao atendente (resumo_atendimento) deve conter SOMENTE dados verídicos, válidos e "
        "realmente informados pelo cliente. Campos não informados devem aparecer como 'Não informado' — nunca preenchidos com suposições."
    )
    partes.append(
        "CLIENTE SEM INTERESSE (regra de respeito): se o cliente deixar CLARO que não tem interesse "
        "— diz que já tem/usa o produto ou um concorrente (ex.: 'já tenho Bradesco grato'), recusa "
        "explicitamente, responde de forma claramente negativa ao assunto, ou pede para não receber "
        "mais mensagens — defina sem_interesse=true. Nesse caso, NÃO insista, NÃO tente contornar a "
        "objeção e NÃO ofereça simulação/migração: apenas responda com UMA mensagem curta, cordial e "
        "respeitosa, agradecendo o retorno e se colocando à disposição caso mude de ideia (ex.: 'Entendo, "
        "obrigada pelo retorno! Qualquer coisa, estou à disposição. 😊'). Mantenha coleta_completa=false. "
        "Em qualquer outra situação (dúvida, objeção contornável, 'agora não posso'), mantenha sem_interesse=false."
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
    llm = ChatOpenAI(api_key=api_key, model="gpt-4.1-mini", temperature=0.5)
    estruturado = llm.with_structured_output(RespostaAssistente)

    mensagens: list = [SystemMessage(content=system_prompt), *historico]
    # Validação determinística de CPF/CNPJ presentes na mensagem → nota para a IA.
    nota = validar_documentos_no_texto(texto_cliente)
    if nota:
        mensagens.append(SystemMessage(content=(
            f"Validação automática de documentos nesta mensagem: {nota} "
            "Se algum estiver INVÁLIDO, informe o cliente com gentileza e peça o número correto; "
            "não registre documentos inválidos no resumo."
        )))
    mensagens.append(HumanMessage(content=texto_cliente))

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
            as_node=LLM_NODE,
        )
    except Exception as e:
        logger.warning("[assistente] falha ao gravar contexto (%s): %s", thread_id, e)

    return resultado


# ── Pausa do atendimento + eco de mensagens enviadas (Redis) ─────────────────
# Chaves seguem o mesmo padrão do contexto: telefone_usuario_instancia (tid).

def _norm(t: str) -> str:
    return " ".join((t or "").split()).lower()[:200]


def _to_str(v) -> str:
    if v is None:
        return ""
    return v.decode() if isinstance(v, (bytes, bytearray)) else str(v)


async def marcar_saida(redis, tid: str, texto: str) -> None:
    """Registra (curta duração) a última mensagem que NÓS enviamos para este contato.

    Serve para reconhecer o 'eco' fromMe que a UAzAPI devolve dos nossos próprios
    envios (campanha, follow-up, resposta da IA) e não confundir com o dono digitando.
    """
    try:
        await redis.set(f"echo:{tid}", _norm(texto), ex=300)
    except Exception as e:
        logger.warning("[assistente] falha ao marcar saída (%s): %s", tid, e)


async def consumir_eco(redis, tid: str, texto: str) -> bool:
    """True se `texto` corresponde à última mensagem que enviamos (eco do nosso envio)."""
    try:
        v = await redis.get(f"echo:{tid}")
        if v is not None and _norm(texto) == _to_str(v):
            await redis.delete(f"echo:{tid}")
            return True
    except Exception as e:
        logger.warning("[assistente] falha ao verificar eco (%s): %s", tid, e)
    return False


async def pausar_atendimento(redis, tid: str, minutos: int) -> None:
    """Pausa o atendimento da IA para este contato por `minutos` (TTL no Redis)."""
    try:
        await redis.set(f"pausa:{tid}", "1", ex=max(1, int(minutos)) * 60)
    except Exception as e:
        logger.warning("[assistente] falha ao pausar (%s): %s", tid, e)


async def esta_pausado(redis, tid: str) -> bool:
    try:
        return bool(await redis.get(f"pausa:{tid}"))
    except Exception as e:
        logger.warning("[assistente] falha ao checar pausa (%s): %s", tid, e)
        return False


# Só consideramos loop quando a mensagem é longa o bastante para ser um template
# de auto-resposta. Mensagens curtas (ex.: "oi", "ok", "sim", "?") NUNCA acionam a
# trava, para jamais silenciar um lead real impaciente.
_LOOP_MIN_LEN = 15


async def detectar_loop_mensagem(
    redis, tid: str, texto: str, *, limite: int = 5, ttl: int = 1800
) -> bool:
    """Detecta loop de auto-resposta (bot-contra-bot): o MESMO contato repetindo a
    MESMA mensagem (longa) várias vezes seguidas. Retorna True SOMENTE quando as
    repetições consecutivas atingem `limite` (5) E a mensagem é longa o bastante
    para ser um template automático — sinal para a IA parar de responder àquele
    número e não ficar em loop infinito (gasto de tokens/mensagens).

    NÃO silencia lead real (cuidado deliberado — só pega loop entre duas IAs):
      • leads mandam mensagens DIFERENTES → o contador zera a cada mensagem nova;
      • mensagens curtas (oi/ok/sim/?) são ignoradas pela trava;
      • assim que chega uma mensagem diferente, a IA volta a responder na hora.
    """
    chave_txt = f"loopmsg_txt:{tid}"
    chave_cnt = f"loopmsg_cnt:{tid}"
    try:
        norm = _norm(texto)
        if len(norm) < _LOOP_MIN_LEN:
            return False
        ultimo = _to_str(await redis.get(chave_txt))
        if ultimo == norm:
            cnt = int(await redis.incr(chave_cnt))
        else:
            cnt = 1
            await redis.set(chave_cnt, 1, ex=ttl)
            await redis.set(chave_txt, norm, ex=ttl)
        # Renova a janela enquanto o loop persiste.
        await redis.expire(chave_cnt, ttl)
        await redis.expire(chave_txt, ttl)
        return cnt >= limite
    except Exception as e:
        logger.warning("[assistente] falha na detecção de loop (%s): %s", tid, e)
        return False


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
