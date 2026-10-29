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

from app.config import ESFORCO_RACIOCINIO, MODELO_OPENAI
from app.graph.build import LLM_NODE, recortar_historico
from app.services.saldo import registrar_resultado_openai

logger = logging.getLogger("uvicorn.error")

# Enviada ao cliente quando a IA não consegue responder (sem saldo, OpenAI fora
# do ar). Quem decide se manda — no máximo 1 vez por hora — é o webhook.
RESPOSTA_FALLBACK = "Recebi sua mensagem! Em breve retornamos com mais informações. 🙏"


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
    """Monta o prompt do sistema a partir da configuração do assistente.

    Cada assistente é independente (1 por instância/número): dados da empresa e
    instrução são os DESTA linha, então o mesmo AI service responde com a
    personalidade que o dono configurou no painel para aquele número. A IDENTIDADE
    do robô (nome próprio, ex.: "Você é a Monalisa...") é definida pelo dono dentro
    da própria instrução — o campo `nome` do assistente é só o rótulo do painel/
    instância (ex.: "SER 0297"), NÃO deve ser imposto como nome de conversa.
    """
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
            "Enquanto a coleta não estiver completa, mantenha coleta_completa=false.\n"
            "O resumo_atendimento deve ser TEXTO PURO: sem markdown, sem asteriscos, sem '#', sem códigos "
            "de formatação/cor. Uma informação por linha (ex.: 'Nome: Lucas'). Campo não informado = 'Não informado'."
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
    usuario_id: str | None = None,
    notas: list[str] | None = None,
) -> RespostaAssistente | None:
    """Gera a resposta do assistente usando o histórico da thread + saída estruturada.

    Lê o histórico pelo checkpointer (mesma thread do disparo), chama o LLM com
    structured output e grava a troca (cliente + assistente) de volta na thread.
    Só a abertura e as mensagens recentes vão para o LLM — ver `recortar_historico`.

    Devolve None quando a IA falhou (sem saldo, fora do ar): o que mandar ao
    cliente nesse caso é decisão do webhook (ver RESPOSTA_FALLBACK).

    `notas` são orientações válidas SÓ para esta mensagem (não vão para o histórico):
    hoje, a instrução customizada de imagem/documento configurada no painel. Ficam
    depois do system prompt e antes da mensagem do cliente, então complementam a
    instrução padrão do assistente em vez de substituí-la.
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
    llm = ChatOpenAI(api_key=api_key, model=MODELO_OPENAI, reasoning_effort=ESFORCO_RACIOCINIO)
    # Mais 1 tentativa quando a saída estruturada vem quebrada (JSON inválido ou
    # fora do schema — tudo ValueError). Há relato no fórum da OpenAI de o
    # gpt-6-luna devolver texto solto junto do JSON em ~3-5% das chamadas; sem
    # isto, o cliente receberia a frase de fallback no meio da coleta. Erro de API
    # (sem saldo, fora do ar) não é ValueError e não é repetido.
    estruturado = llm.with_structured_output(RespostaAssistente).with_retry(
        retry_if_exception_type=(ValueError,), stop_after_attempt=2,
    )

    mensagens: list = [SystemMessage(content=system_prompt), *recortar_historico(historico)]
    for nota_extra in (notas or []):
        if (nota_extra or "").strip():
            mensagens.append(SystemMessage(content=nota_extra.strip()))
    # Validação determinística de CPF/CNPJ presentes na mensagem → nota para a IA.
    nota = validar_documentos_no_texto(texto_cliente)
    if nota:
        mensagens.append(SystemMessage(content=(
            f"Validação automática de documentos nesta mensagem: {nota} "
            "Se algum estiver INVÁLIDO, informe o cliente com gentileza e peça o número correto; "
            "não registre documentos inválidos no resumo."
        )))
    mensagens.append(HumanMessage(content=texto_cliente))

    resultado: RespostaAssistente | None
    try:
        resultado = await estruturado.ainvoke(mensagens)
        await registrar_resultado_openai(usuario_id, sucesso=True)
    except Exception as e:
        await registrar_resultado_openai(usuario_id, sucesso=False, erro=e)
        logger.exception("[assistente] erro ao gerar resposta: %s", e)
        resultado = None

    # Grava a troca na thread para manter o contexto. Se a IA falhou, grava só o
    # cliente: a frase de fallback não é conversa, e no histórico ela só ensinava
    # a IA a repeti-la (no loop da Emdia ela entrou 2 mil vezes na thread).
    novas: list = [HumanMessage(content=texto_cliente)]
    if resultado is not None:
        novas.append(AIMessage(content=resultado.resposta))
    try:
        await graph.aupdate_state(cfg_run, {"messages": novas}, as_node=LLM_NODE)
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
    """Pausa AUTOMÁTICA (o dono/profissional respondeu pelo celular). TTL no Redis.

    Nunca sobrescreve uma pausa MANUAL ativa (definida no painel, ver
    `pausar_atendimento_manual`) — evita que o próprio profissional encurte, sem
    querer, uma pausa que o dono configurou deliberadamente (ex.: "10 dias")."""
    try:
        if await redis.get(f"pausa_manual:{tid}"):
            return
        await redis.set(f"pausa:{tid}", "1", ex=max(1, int(minutos)) * 60)
    except Exception as e:
        logger.warning("[assistente] falha ao pausar (%s): %s", tid, e)


async def pausar_atendimento_manual(redis, tid: str, minutos: int) -> None:
    """Pausa MANUAL (botão "Pausar" no painel de Conversas) — tem prioridade sobre
    a automática: marca as duas chaves, e `pausar_atendimento` respeita o marcador."""
    ttl = max(1, int(minutos)) * 60
    await redis.set(f"pausa:{tid}", "1", ex=ttl)
    await redis.set(f"pausa_manual:{tid}", "1", ex=ttl)


async def despausar_manual(redis, tid: str) -> None:
    """Remove a pausa (manual ou automática) de uma conversa específica."""
    await redis.delete(f"pausa:{tid}")
    await redis.delete(f"pausa_manual:{tid}")
    await limpar_trava_loop(redis, tid)


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

# Limites da trava anti-loop (o webhook cita os mesmos no aviso ao atendente).
LOOP_REPETICOES = 5          # mesma mensagem longa N vezes...
LOOP_JANELA_MIN = 30         # ...dentro desta janela
TETO_RESPOSTAS_HORA = 60     # respostas da IA ao mesmo contato em 1 hora


async def detectar_loop_mensagem(
    redis, tid: str, texto: str, *, limite: int = LOOP_REPETICOES, ttl: int = LOOP_JANELA_MIN * 60
) -> bool:
    """Detecta loop de auto-resposta (bot-contra-bot): o MESMO contato mandando a
    MESMA mensagem (longa) `limite` (5) vezes na janela — seguidas OU NÃO. True é
    o sinal para o webhook pausar a IA nesta conversa e chamar um humano.

    Antes só contava repetições SEGUIDAS, e os dois loops reais que passaram
    (Anhanguera em 14/10/2026, Emdia em 28/10/2026) eram robôs que giram um ciclo
    de mensagens diferentes ("pede CPF" → "não validei" → "encerra" → recomeça):
    o contador zerava a cada troca e nunca chegava a 5. Agora cada texto tem a
    sua própria contagem. A janela renova a cada mensagem longa do contato.

    NÃO pega lead real (cuidado deliberado):
      • medido no banco (120 dias até 29/10/2026), nenhum cliente real repetiu a
        mesma mensagem longa nem 3 vezes em 30 minutos — todos eram robôs;
      • mensagens curtas (oi/ok/sim/?) continuam fora da trava;
      • e se algum dia pegar, a conversa vai para um humano, não fica no vácuo.
    """
    chave = f"loopmsg:{tid}"
    try:
        norm = _norm(texto)
        if len(norm) < _LOOP_MIN_LEN:
            return False
        cnt = int(await redis.hincrby(chave, norm, 1))
        await redis.expire(chave, ttl)
        return cnt >= limite
    except Exception as e:
        logger.warning("[assistente] falha na detecção de loop (%s): %s", tid, e)
        return False


async def ia_passou_do_limite(
    redis, tid: str, *, limite: int = TETO_RESPOSTAS_HORA, janela: int = 3600
) -> bool:
    """Teto de respostas da IA por contato: True quando esta seria a resposta
    nº `limite`+1 (61ª) dentro da janela de 1 hora, que começa na 1ª resposta.

    Rede de segurança para o loop que a detecção por repetição não reconhecer
    (robô que varia o texto a cada mensagem). Medido no banco em 29/10/2026: o
    pico de um cliente real foi 35 respostas numa hora; os robôs passaram de 150.

    Cada chamada conta uma resposta — chame só quando a IA for de fato responder.
    """
    chave = f"ia_resp:{tid}"
    try:
        # SET NX antes do INCR: o TTL nasce junto com a chave (INCR o preserva),
        # então o contador nunca fica eterno se uma chamada falhar no meio.
        await redis.set(chave, 0, ex=janela, nx=True)
        return int(await redis.incr(chave)) > limite
    except Exception as e:
        logger.warning("[assistente] falha no teto de respostas (%s): %s", tid, e)
        return False


async def limpar_trava_loop(redis, tid: str) -> None:
    """Zera os contadores da trava anti-loop. Chamado ao despausar: se o dono
    liberou a conversa, ela recomeça do zero (senão a próxima mensagem já
    pausaria de novo pelo contador antigo)."""
    try:
        await redis.delete(f"loopmsg:{tid}", f"ia_resp:{tid}", f"loop_aviso:{tid}")
    except Exception as e:
        logger.warning("[assistente] falha ao limpar trava anti-loop (%s): %s", tid, e)


# ── Agrupamento de mensagens em rajada (debounce) ───────────────────────────
# O cliente quebra o raciocínio em várias mensagens seguidas ("29 anos" / "só
# eu"). Cada uma chega num webhook próprio e vira uma task independente — sem
# coordenação a IA respondia uma vez POR MENSAGEM, mandando duas respostas quase
# idênticas com meio segundo de diferença (e pagando dois LLM).
#
# Aqui cada mensagem entra numa fila e espera a janela. Quem chega depois
# incrementa a "geração"; ao acordar, só responde a task cuja geração ainda é a
# última — as demais desistem em silêncio, e o texto delas vai junto na resposta
# de quem ganhou. Tem que ser no Redis (não em memória): o serviço sobe com
# `--workers 2` e as duas mensagens podem cair em processos diferentes.
#
# Os dois passos são Lua porque o Redis executa o script inteiro sem
# interrupção. Enfileirar precisa ser atômico junto com o INCR: se outra task
# conseguisse empilhar o texto DEPOIS do drenar e incrementar a geração ANTES,
# ela acharia a fila vazia ao acordar e responderia de novo — a duplicata que
# estamos justamente removendo.

_ENFILEIRAR_LUA = """
redis.call('RPUSH', KEYS[1], ARGV[1])
redis.call('EXPIRE', KEYS[1], ARGV[2])
local g = redis.call('INCR', KEYS[2])
redis.call('EXPIRE', KEYS[2], ARGV[2])
return g
"""

# Só drena se a geração ainda for a desta task; senão devolve nil (outra
# mensagem chegou e ela responde por todas, com o texto desta junto).
_DRENAR_LUA = """
if redis.call('GET', KEYS[2]) ~= ARGV[1] then return nil end
local itens = redis.call('LRANGE', KEYS[1], 0, -1)
redis.call('DEL', KEYS[1])
redis.call('DEL', KEYS[2])
return itens
"""


async def enfileirar_mensagem(redis, tid: str, texto: str, *, ttl: int = 600) -> str | None:
    """Enfileira `texto` e devolve a geração desta task (para `coletar_rajada`).

    None quando o Redis falha: o chamador responde na hora, sem agrupar — que é
    o comportamento antigo. Melhor responder duas vezes do que ficar calado.
    """
    try:
        gen = await redis.eval(_ENFILEIRAR_LUA, 2, f"buf:{tid}", f"bufgen:{tid}", texto, ttl)
        return str(gen)
    except Exception as e:
        logger.warning("[assistente] falha ao enfileirar rajada (%s): %s", tid, e)
        return None


async def coletar_rajada(redis, tid: str, geracao: str | None, *, proprio: str) -> list[str] | None:
    """Fecha a janela. Devolve os textos a responder, ou None se esta task perdeu
    (outra mensagem chegou depois e vai responder por ela).

    None significa SEMPRE "outra task responde" — nunca erro de Redis. Falha de
    Redis cai no texto próprio, para não engolir a resposta ao cliente.
    """
    if geracao is None:
        return [proprio]
    try:
        itens = await redis.eval(_DRENAR_LUA, 2, f"buf:{tid}", f"bufgen:{tid}", geracao)
    except Exception as e:
        logger.warning("[assistente] falha ao drenar rajada (%s): %s", tid, e)
        return [proprio]
    if itens is None:
        return None
    # Fila vazia só acontece se o TTL estourou; responder o próprio texto é o certo.
    return [t for t in itens if (t or "").strip()] or [proprio]


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
