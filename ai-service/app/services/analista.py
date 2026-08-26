"""Analista de Atendimento — responde perguntas sobre o histórico comercial.

Arquitetura (e por que ela é assim):

  pergunta → LLM escolhe uma FERRAMENTA → SQL fixo roda → LLM lê o retorno → texto

O LLM nunca escreve SQL e nunca vê o banco. Ele escolhe entre as funções de
`analista_consultas` e passa parâmetros; `usuario_id` é injetado aqui pelo
servidor, a partir do JWT já validado no Nuxt — jamais vem do texto digitado.
Isso resolve de uma vez o isolamento entre empresas e a injeção de prompt (o
conteúdo de `mensagens` é escrito por terceiros e é entrada não confiável).

Dois números NUNCA saem do LLM, sempre do código:
  • `rastro`    — o que de fato rodou, montado a partir das tool calls reais.
  • `cobertura` — quanto do histórico é ilegível (áudio sem transcrição).
Se viessem do texto gerado, o modelo poderia arredondar, esquecer ou inventar
justamente a informação que serve para desconfiar dele.
"""

import json
import logging

from openai import AsyncOpenAI

from app.services import analista_consultas as q
from app.services import saldo

logger = logging.getLogger("uvicorn.error")

MODELO = "gpt-4.1-mini"
MAX_VOLTAS = 5          # teto de idas ao LLM (evita laço infinito de tool calls)
MAX_HISTORICO = 8       # turnos anteriores enviados junto (contexto da conversa)


SYSTEM = """Você é o Analista de Atendimento de uma empresa que vende por WhatsApp.
O dono da empresa conversa com você para entender como andam os atendimentos.

COMO TRABALHAR
- Use as ferramentas para buscar os dados. Nunca invente número, nome ou data.
- Se precisar de mais de uma ferramenta, chame quantas forem necessárias.
- Se a pergunta for sobre um telefone, use buscar_conversa_por_telefone e depois
  timeline_conversa para ler a conversa antes de opinar.
- Se não achar o dado, diga que não achou e explique o que faltou. Nunca preencha
  buraco com suposição apresentada como fato.

VENDEDOR = profissional com número/instância próprio. "Atendente", "corretor",
"consultor" e "profissional" significam a mesma coisa aqui.

COBERTURA (regra mais importante)
Parte das mensagens é áudio sem transcrição ou imagem sem legenda — elas chegam
com texto vazio. Quando `sem_conteudo` ou `msgs_sem_texto` for maior que zero,
diga isso de forma clara logo no começo da resposta, com o número. Nunca conclua
sobre a qualidade de um atendimento como se tivesse lido tudo quando não leu.

CHANCE DE FECHAMENTO
Descreva SINAIS observados, citando a mensagem que originou cada um. Nunca dê
porcentagem ("70% de chance") — não existe histórico de desfecho no sistema para
sustentar previsão. Sinais favoráveis e contrários, sem inventar placar.

TEMPO
Os campos "..._ha" e "parada_ha" já vêm calculados. Use-os como estão em vez de
recalcular a partir das datas.

COMO ESCREVER
- Português do Brasil, direto, sem rodeio nem elogio ao usuário.
- Markdown: **negrito** para o que importa, listas e tabelas quando ajudar.
- Comece pela conclusão. Depois o detalhe.
- Termine com "**Próxima ação:**" e uma recomendação concreta e acionável.
- Não repita o rastro das consultas: a interface já mostra isso ao lado.
"""


# ── Ferramentas expostas ao LLM ──────────────────────────────────────────────
# `usuario_id` NÃO aparece em nenhum schema de propósito: o modelo não pode
# escolher de qual empresa ler. Ele é injetado no dispatcher.

FERRAMENTAS = [
    {
        "type": "function",
        "function": {
            "name": "resumo_operacao",
            "description": "Visão geral da operação: conversas ativas, movimento nas últimas 24h, paradas há mais de 3 dias, canais conectados, tempo médio de resposta e desde quando existe histórico. Use para perguntas amplas ('como está tudo?', 'como foi a semana?').",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_conversa_por_telefone",
            "description": "Encontra a conversa de um cliente pelo telefone. Aceita qualquer formato (com ou sem DDI/DDD/máscara).",
            "parameters": {
                "type": "object",
                "properties": {"telefone": {"type": "string", "description": "Telefone do cliente, ex: '11989444136'"}},
                "required": ["telefone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_conversas",
            "description": "Busca conversas pelo NOME do cliente (parcial, tolera acento e erro de digitação).",
            "parameters": {
                "type": "object",
                "properties": {"termo": {"type": "string"}},
                "required": ["termo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "timeline_conversa",
            "description": "Lê as mensagens de uma conversa em ordem cronológica. Informa quais mensagens não têm conteúdo legível (áudio sem transcrição). Use depois de achar a conversa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "conversa_id": {"type": "string"},
                    "limite": {"type": "integer", "description": "Máximo de mensagens (padrão 60)"},
                },
                "required": ["conversa_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_vendedor",
            "description": "Encontra vendedores pelo nome (parcial). Retorna também o status do canal WhatsApp dele.",
            "parameters": {
                "type": "object",
                "properties": {"nome": {"type": "string"}},
                "required": ["nome"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "metricas_vendedor",
            "description": "Números de UM vendedor: carteira, conversas ativas, paradas, tempo médio de resposta e quanto do conteúdo dele é ilegível. Exige o id vindo de buscar_vendedor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendedor_id": {"type": "string"},
                    "dias": {"type": "integer", "description": "Período em dias (padrão 30)"},
                },
                "required": ["vendedor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ranking_vendedores",
            "description": "Todos os vendedores lado a lado: carteira, atividade, conversas paradas, tempo de resposta e status do canal. Use para comparar ou achar quem está sem movimento.",
            "parameters": {
                "type": "object",
                "properties": {"dias": {"type": "integer", "description": "Período em dias (padrão 30)"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "conversas_paradas",
            "description": "Conversas abertas sem interação há mais de N dias. Diz de quem foi a última mensagem (se do cliente, a bola está com o vendedor).",
            "parameters": {
                "type": "object",
                "properties": {
                    "dias": {"type": "integer", "description": "Padrão 3"},
                    "vendedor_id": {"type": "string", "description": "Opcional: filtrar por um vendedor"},
                },
            },
        },
    },
]

_DISPATCH = {
    "resumo_operacao": q.resumo_operacao,
    "buscar_conversa_por_telefone": q.buscar_conversa_por_telefone,
    "buscar_conversas": q.buscar_conversas,
    "timeline_conversa": q.timeline_conversa,
    "buscar_vendedor": q.buscar_vendedor,
    "metricas_vendedor": q.metricas_vendedor,
    "ranking_vendedores": q.ranking_vendedores,
    "conversas_paradas": q.conversas_paradas,
}


def _resumir_saida(nome: str, dados: dict) -> str:
    """Rótulo curto do resultado, para o rastro que aparece na interface."""
    try:
        if nome == "timeline_conversa":
            return f"{dados.get('cobertura', {}).get('total', 0)} mensagens"
        if nome in ("buscar_conversa_por_telefone",):
            return f"{len(dados.get('conversas', []))} conversa(s)"
        if nome == "buscar_conversas":
            return f"{len(dados.get('conversas', []))} conversa(s)"
        if nome == "buscar_vendedor":
            return f"{len(dados.get('vendedores', []))} vendedor(es)"
        if nome == "ranking_vendedores":
            return f"{len(dados.get('vendedores', []))} vendedores"
        if nome == "conversas_paradas":
            return f"{len(dados.get('conversas', []))} conversa(s)"
        if nome == "metricas_vendedor":
            return f"{dados.get('conversas', 0)} conversas"
        if nome == "resumo_operacao":
            return f"{dados.get('ativas', 0)} ativas"
    except Exception:
        pass
    return "ok"


def _extrair_cobertura(nome: str, dados: dict) -> dict | None:
    """Cobertura vinda do CÓDIGO, nunca do texto do modelo.

    É o número que autoriza (ou não) confiar no diagnóstico, então ele não pode
    depender de o LLM ter lembrado de repeti-lo corretamente.
    """
    try:
        if nome == "timeline_conversa":
            c = dados.get("cobertura") or {}
            if c.get("total"):
                return {"total": c["total"], "lidas": c.get("lidas", 0), "sem_conteudo": c.get("sem_conteudo", 0)}
        if nome in ("metricas_vendedor", "resumo_operacao"):
            tot, sem = dados.get("total_msgs"), dados.get("msgs_sem_texto")
            if tot:
                return {"total": tot, "lidas": tot - (sem or 0), "sem_conteudo": sem or 0}
    except Exception:
        pass
    return None


async def perguntar(
    *,
    usuario_id: str,
    pergunta: str,
    api_key: str,
    historico: list[dict] | None = None,
) -> dict:
    """Responde uma pergunta sobre os atendimentos.

    Retorna {resposta, rastro, cobertura, titulo}. `rastro` e `cobertura` são
    montados a partir das chamadas reais, não do que o modelo escreveu.
    """
    cliente = AsyncOpenAI(api_key=api_key)

    mensagens: list[dict] = [{"role": "system", "content": SYSTEM}]
    for h in (historico or [])[-MAX_HISTORICO:]:
        papel = h.get("papel")
        texto = (h.get("texto") or "").strip()
        if papel in ("user", "assistant") and texto:
            mensagens.append({"role": papel, "content": texto[:4000]})
    mensagens.append({"role": "user", "content": pergunta})

    rastro: list[dict] = []
    cobertura: dict | None = None

    try:
        for volta in range(MAX_VOLTAS):
            resp = await cliente.chat.completions.create(
                model=MODELO,
                messages=mensagens,
                tools=FERRAMENTAS,
                temperature=0.2,
            )
            escolha = resp.choices[0].message
            chamadas = escolha.tool_calls or []

            if not chamadas:
                await saldo.registrar_resultado_openai(usuario_id, sucesso=True)
                return {
                    "resposta": (escolha.content or "").strip() or "Não consegui montar uma resposta.",
                    "rastro": rastro,
                    "cobertura": cobertura,
                    "titulo": _titulo(pergunta),
                }

            mensagens.append({
                "role": "assistant",
                "content": escolha.content,
                "tool_calls": [
                    {"id": c.id, "type": "function",
                     "function": {"name": c.function.name, "arguments": c.function.arguments}}
                    for c in chamadas
                ],
            })

            for c in chamadas:
                nome = c.function.name
                fn = _DISPATCH.get(nome)
                try:
                    args = json.loads(c.function.arguments or "{}")
                except Exception:
                    args = {}

                if not fn:
                    dados = {"erro": f"ferramenta desconhecida: {nome}"}
                else:
                    try:
                        # usuario_id é injetado AQUI — o modelo não escolhe empresa.
                        dados = await fn(usuario_id=usuario_id, **args)
                    except TypeError as e:
                        dados = {"erro": f"parâmetros inválidos: {e}"}
                    except Exception as e:
                        logger.warning("[analista] falha em %s(%s): %s", nome, args, e)
                        dados = {"erro": "falha ao consultar o banco"}

                if not dados.get("erro"):
                    rastro.append({
                        "fn": nome,
                        "args": ", ".join(f"{k}={v}" for k, v in args.items()) or "—",
                        "resultado": _resumir_saida(nome, dados),
                    })
                    cobertura = _extrair_cobertura(nome, dados) or cobertura

                mensagens.append({
                    "role": "tool",
                    "tool_call_id": c.id,
                    "content": json.dumps(dados, ensure_ascii=False, default=str)[:24000],
                })

        # Estourou o teto de voltas: devolve o que der, sem travar o usuário.
        await saldo.registrar_resultado_openai(usuario_id, sucesso=True)
        return {
            "resposta": "A consulta ficou longa demais e parei no meio. Tente uma pergunta mais específica.",
            "rastro": rastro,
            "cobertura": cobertura,
            "titulo": _titulo(pergunta),
        }

    except Exception as e:
        await saldo.registrar_resultado_openai(usuario_id, sucesso=False, erro=e)
        logger.exception("[analista] erro ao responder: %s", e)
        if saldo.e_erro_de_saldo(e):
            raise RuntimeError(
                "A conta da OpenAI está sem saldo. Recarregue em platform.openai.com "
                "para o analista voltar a responder."
            ) from e
        raise RuntimeError("Não consegui consultar os atendimentos agora. Tente de novo em instantes.") from e


def _titulo(pergunta: str) -> str:
    """Nome curto do relatório — vira o título do PDF exportado."""
    p = " ".join((pergunta or "").split())
    return (p[:70] + "…") if len(p) > 70 else (p or "Análise de atendimento")
