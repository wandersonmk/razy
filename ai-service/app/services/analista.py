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
import re
from datetime import datetime, timedelta, timezone

from openai import AsyncOpenAI

from app.services import analista_consultas as q
from app.services import saldo

logger = logging.getLogger("uvicorn.error")

MODELO = "gpt-4.1-mini"
MAX_VOLTAS = 5          # teto de idas ao LLM (evita laço infinito de tool calls)
MAX_HISTORICO = 8       # turnos anteriores enviados junto (contexto da conversa)

# Fuso do negócio. O banco e o container rodam em UTC; sem converter, uma
# mensagem das 22:29 aparece como 01:29 do dia seguinte no relatório.
# `zoneinfo` depende do tzdata do sistema — cai para UTC-3 fixo se faltar.
try:
    from zoneinfo import ZoneInfo
    FUSO_BR = ZoneInfo("America/Sao_Paulo")
except Exception:  # noqa: BLE001
    FUSO_BR = timezone(timedelta(hours=-3))


SYSTEM = """Você é o Analista de Atendimento de uma empresa que vende por WhatsApp.
O dono da empresa conversa com você para entender como andam os atendimentos.

COMO TRABALHAR
- Use as ferramentas para buscar os dados. Nunca invente número, nome ou data.
- Se precisar de mais de uma ferramenta, chame quantas forem necessárias.
- Se a pergunta for sobre um telefone, use buscar_conversa_por_telefone e depois
  timeline_conversa para ler a conversa antes de opinar.
- NÃO repita a mesma busca em outro formato: as ferramentas já normalizam
  telefone (com/sem DDI, com/sem nono dígito). Uma chamada basta.
- Se não achar o dado, diga que não achou e explique o que faltou. Nunca preencha
  buraco com suposição apresentada como fato.

VÁRIAS CONVERSAS PARA O MESMO NÚMERO
Quando `varias_conversas` for true, o cliente falou com mais de um vendedor
(uma conversa por canal). Diga isso e trate cada uma, ou pergunte qual interessa
— não escolha uma em silêncio. Se `correspondencia_aproximada` for true, o
número foi casado só pelos últimos dígitos: avise que pode não ser essa pessoa.

HISTÓRICO CURTO
`historico_desde` (em resumo_operacao) diz desde quando existe registro. Nada
antes disso existe no banco. Não compare períodos que caem fora dessa janela nem
conclua "caiu em relação ao mês passado" se o mês passado não foi gravado.

VENDEDOR = profissional com número/instância próprio. "Atendente", "corretor",
"consultor" e "profissional" significam a mesma coisa aqui.

COBERTURA
Parte das mensagens é áudio sem transcrição ou imagem sem legenda — elas chegam
com texto vazio. Se `sem_conteudo` (ou `msgs_sem_texto`) for MAIOR QUE ZERO,
avise no começo quantas mensagens você não conseguiu ler e não conclua sobre a
qualidade do atendimento como se tivesse lido tudo.
Se for ZERO, NÃO mencione o assunto. Escrever "não há mensagens sem conteúdo
legível" só confunde quem lê: a pessoa não sabe do que você está falando e o
aviso ocupa espaço sem informar nada.

CHANCE DE FECHAMENTO
Descreva SINAIS observados, citando a mensagem que originou cada um. Nunca dê
porcentagem ("70% de chance") — não existe histórico de desfecho no sistema para
sustentar previsão. Sinais favoráveis e contrários, sem inventar placar.

TEMPO
NUNCA calcule diferença de datas você mesmo — os campos "..._ha", "parada_ha",
"cliente_falou_ha" e "vendedor_falou_ha" já vêm prontos, medidos contra o
relógio do banco. Use-os como estão.
Para FILTRAR por tempo, use o parâmetro `horas` de conversas_paradas: "parada há
1 hora" = horas=1, "há 3 dias" = horas=72, "esta semana" = horas=168. Não
arredonde a pergunta para dias.

`horas` é um PISO, não um alvo exato. "Parada há 1 hora" quer dizer "há 1 hora
ou mais" — uma conversa parada há 11 horas ENTRA nessa resposta. Se a ferramenta
devolver conversas, elas SÃO a resposta: liste-as. Nunca responda "não há
nenhuma" porque as encontradas estão paradas há mais tempo do que foi pedido —
esse é o resultado certo, não um resultado vazio.

Use `total_encontrado` para dizer quantas são. Quando `lista_truncada` for true,
você recebeu só as mais antigas: diga o total e mostre essas, sem dar a entender
que a lista está completa.

COMO ESCREVER
- Português do Brasil, direto, sem rodeio nem elogio ao usuário.
- Frases curtas. Cada item de lista é uma ideia, não um parágrafo.
- Comece pela conclusão. Depois o detalhe.

FORMATO DA RESPOSTA (obrigatório)
Responda em JSON com uma lista de `cards`. Use SÓ os cards que a pergunta
justifica — card sem conteúdo útil não deve existir. Ordem sugerida:

- `resumo` — o que aconteceu, em ordem cronológica, em itens curtos.
- `coletado` — dados que o cliente forneceu (produto/serviço procurado,
  necessidade, faixa de preço, CNPJ/cadastro, preferências). Pares
  rótulo/valor. SÓ inclua se o cliente realmente informou algo.
- `interesse` — `nivel` "alta", "media" ou "baixa" + os sinais que
  justificam, em itens. Sinais concretos tirados das mensagens.
- `atencao` — problemas: demora para responder, pergunta ignorada, sem
  follow-up, orçamento não enviado, atendimento interrompido, cliente
  esperando, falha da IA, conversa parada. Preencha `nivel`: "alta" se há
  algo grave (cliente esperando há dias, pergunta sem resposta), "media"
  para pendência leve, "baixa" quando o atendimento transcorreu normalmente
  — nesse caso, um único item dizendo isso. A cor do card segue esse nível.
- `proxima_acao` — uma recomendação concreta, em `texto`.

Para perguntas que NÃO são sobre uma conversa específica (comparar
vendedores, funil, período), use `resumo`, `atencao` e `proxima_acao`, e
apresente números em `campos` quando ajudar.

NÃO monte card de visão geral do cliente: nome, telefone, datas e contagem
de mensagens são preenchidos pelo sistema, fora do seu texto.

TÍTULOS: use o nome da seção e pronto ("Resumo da conversa", "Pontos de
atenção"). Não escreva telefone no título — o sistema acrescenta o nome do
cliente e o número já com a máscara certa.
"""


# Esquema fechado da resposta. Estruturar aqui, e não deixar a interface
# adivinhar seções dentro de um texto corrido, é o que permite montar os cards
# sem heurística frágil de parsing.
ESQUEMA_RESPOSTA = {
    "type": "json_schema",
    "json_schema": {
        "name": "analise",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["cards"],
            "properties": {
                "cards": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["tipo", "titulo", "nivel", "texto", "itens", "campos"],
                        "properties": {
                            "tipo": {
                                "type": "string",
                                "enum": ["resumo", "coletado", "interesse", "atencao", "proxima_acao"],
                            },
                            "titulo": {"type": "string"},
                            "nivel": {
                                "type": ["string", "null"],
                                "enum": ["alta", "media", "baixa", None],
                                "description": (
                                    "Em `interesse`: chance de fechamento. Em `atencao`: "
                                    "gravidade (baixa = tudo normal). Nulo nos demais."
                                ),
                            },
                            "texto": {"type": ["string", "null"]},
                            "itens": {"type": "array", "items": {"type": "string"}},
                            "campos": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["rotulo", "valor"],
                                    "properties": {
                                        "rotulo": {"type": "string"},
                                        "valor": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                }
            },
        },
    },
}


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
            "description": "Encontra a conversa de um cliente pelo telefone. Aceita qualquer formato (com ou sem DDI/DDD/máscara) e já testa as variantes do número, então NÃO reescreva nem complete o telefone.",
            "parameters": {
                "type": "object",
                "properties": {"telefone": {
                    "type": "string",
                    "description": (
                        "O telefone COPIADO LITERALMENTE da pergunta, com máscara e tudo "
                        "(ex.: '+55 14 98138-6372'). Não remova dígitos, não tire o DDI e "
                        "não tente adivinhar o formato — a ferramenta normaliza sozinha."
                    ),
                }},
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
            "description": (
                "Conversas abertas paradas há N horas OU MAIS. `horas` é um piso, "
                "não um alvo exato: com horas=1 vêm também as paradas há 11h ou 3 dias. "
                "Devolve `total_encontrado` (total real) e `conversas` (as mais antigas). "
                "Diz de quem foi a última mensagem — se do cliente, a bola está com o vendedor."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "horas": {
                        "type": "integer",
                        "description": "Piso em HORAS. 1 hora = 1, 1 dia = 24, 3 dias = 72, 1 semana = 168. Padrão 72.",
                    },
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


def _chave_cache(nome: str, args: dict) -> str:
    """Identidade de uma chamada, ignorando diferenças de formatação.

    Telefone entra só com os dígitos: para o banco, "556291366367" e
    "+55 62 9136-6367" são a mesma busca, e o modelo alterna entre as duas
    formas. O resto vai em minúsculas e sem espaços nas pontas.
    """
    partes = []
    for k in sorted(args):
        v = args[k]
        if isinstance(v, str):
            v = re.sub(r"\D", "", v) if "telefone" in k else v.strip().lower()
        partes.append(f"{k}={v}")
    return nome + "|" + "&".join(partes)


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


# Quanto MAIOR, mais específica é a cobertura daquela consulta. A barra exibida
# tem de falar do recorte que a resposta analisou: se o modelo pergunta a
# timeline de uma conversa e depois puxa o resumo geral, a cobertura da conversa
# é a que importa — a global sobrescrevendo daria a impressão errada de que o
# diagnóstico daquele cliente foi feito lendo 80% de tudo.
_PESO_COBERTURA = {"resumo_operacao": 1, "metricas_vendedor": 2, "timeline_conversa": 3}


def _extrair_cobertura(nome: str, dados: dict) -> tuple[int, dict] | None:
    """Cobertura vinda do CÓDIGO, nunca do texto do modelo.

    É o número que autoriza (ou não) confiar no diagnóstico, então ele não pode
    depender de o LLM ter lembrado de repeti-lo corretamente. Retorna
    (peso, cobertura) para o chamador manter sempre a mais específica.
    """
    try:
        if nome == "timeline_conversa":
            c = dados.get("cobertura") or {}
            if c.get("total"):
                return _PESO_COBERTURA[nome], {
                    "total": c["total"], "lidas": c.get("lidas", 0),
                    "sem_conteudo": c.get("sem_conteudo", 0),
                }
        if nome in ("metricas_vendedor", "resumo_operacao"):
            tot, sem = dados.get("total_msgs"), dados.get("msgs_sem_texto")
            if tot:
                return _PESO_COBERTURA[nome], {
                    "total": tot, "lidas": tot - (sem or 0), "sem_conteudo": sem or 0,
                }
    except Exception:
        pass
    return None


def _tel_legivel(numero: str | None) -> str:
    """Telefone na máscara brasileira: (14) 98138-6372.

    Trata os dois formatos que convivem na base: celular com nono dígito
    (9 dígitos após o DDD) e número antigo sem ele (8 dígitos). Número que
    não se encaixa em nenhum dos dois volta só com os dígitos — melhor sem
    máscara do que com máscara errada.
    """
    d = re.sub(r"\D", "", numero or "")
    if not d:
        return "—"
    nac = d[2:] if d.startswith("55") and len(d) in (12, 13) else d
    if len(nac) not in (10, 11):
        return d
    ddd, resto = nac[:2], nac[2:]
    if len(resto) == 9:                       # com nono dígito
        return f"({ddd}) {resto[:5]}-{resto[5:]}"
    return f"({ddd}) {resto[:4]}-{resto[4:]}"  # sem nono dígito


def _identidade(conversa: dict | None) -> str:
    """'GABRIEL - VITA VERDE · (14) 98138-6372' — para os títulos dos cards."""
    if not conversa:
        return ""
    nome = (conversa.get("nome_contato") or "").strip()
    tel = _tel_legivel(conversa.get("numero"))
    if nome and tel != "—":
        return f"{nome} · {tel}"
    return nome or tel


def _data_curta(iso: str | None) -> str:
    """Data no fuso de Brasília.

    O banco guarda em UTC e o container roda em UTC, então `astimezone()` sem
    fuso mostrava 01:29 para uma mensagem que o dono vê como 22:29 na própria
    tela de Conversas. Data que não bate com o WhatsApp destrói a confiança no
    relatório inteiro.
    """
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).astimezone(FUSO_BR).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "—"


def _card_visao_geral(conversa: dict | None, timeline: dict | None) -> dict | None:
    """Visão geral montada pelo CÓDIGO, a partir do retorno das consultas.

    Nome, telefone, atendente, datas e contagem de mensagens são fato puro —
    justamente o tipo de campo que um modelo troca ou arredonda sem querer. Por
    isso o prompt proíbe o LLM de produzir este card.
    """
    if not conversa:
        return None

    total = None
    if timeline:
        total = (timeline.get("cobertura") or {}).get("total")
    if total is None:
        total = conversa.get("total_msgs")

    if conversa.get("resolved_at"):
        status = "Resolvido"
    elif conversa.get("arquivada"):
        status = "Arquivado"
    elif conversa.get("opened_at"):
        status = "Em atendimento"
    else:
        status = "Aberto"

    # Separa os dois lados: "último contato" sozinho não diz se quem falou por
    # último foi o cliente (e está esperando) ou a equipe (e a bola está com ele).
    ult_cliente = conversa.get("ultima_msg_cliente_em")
    ult_vendedor = conversa.get("ultima_msg_vendedor_em")
    esperando = conversa.get("cliente_aguardando_resposta")

    campos = [
        {"rotulo": "Cliente", "valor": conversa.get("nome_contato") or "sem nome"},
        {"rotulo": "Telefone", "valor": _tel_legivel(conversa.get("numero"))},
        {"rotulo": "Atendente", "valor": conversa.get("vendedor") or "sem atendente atribuído"},
        {"rotulo": "Primeiro contato", "valor": _data_curta(conversa.get("opened_at") or conversa.get("created_at"))},
        {
            "rotulo": "Cliente falou por último",
            "valor": f"{_data_curta(ult_cliente)}  ({conversa.get('cliente_falou_ha')})"
            if ult_cliente else "—",
        },
        {
            "rotulo": "Atendente respondeu",
            "valor": f"{_data_curta(ult_vendedor)}  ({conversa.get('vendedor_falou_ha')})"
            if ult_vendedor else "ainda não respondeu",
        },
        {"rotulo": "Mensagens", "valor": str(total) if total is not None else "—"},
        {"rotulo": "Sem interação há", "valor": conversa.get("sem_interacao_ha") or "—"},
        {
            "rotulo": "Status",
            "valor": f"{status} · cliente aguardando" if esperando else status,
        },
    ]
    return {"tipo": "visao_geral", "titulo": "Visão geral", "nivel": None,
            "texto": None, "itens": [], "campos": campos}


def _primeiro_nome(nome: str | None, alternativo: str = "—") -> str:
    """Rótulo curto para o eixo do gráfico — nome inteiro não cabe na barra."""
    n = (nome or "").strip()
    if not n:
        return alternativo
    partes = n.split()
    return partes[0][:14] if partes else alternativo


def _extrair_graficos(nome: str, dados: dict) -> list[dict]:
    """Monta os gráficos a partir do retorno REAL da consulta.

    Mesma regra do rastro e da cobertura: o número plotado sai do banco, nunca
    do texto do modelo. Um gráfico com valor inventado é pior que gráfico
    nenhum — ele passa credibilidade que o dado não tem.

    Devolve uma especificação neutra (tipo/labels/séries); quem escolhe cor
    concreta e estilo é o componente, que sabe o tema em que está desenhando.
    """
    try:
        if nome == "ranking_vendedores":
            vs = [v for v in dados.get("vendedores", []) if (v.get("conversas") or 0) > 0]
            if len(vs) < 2:
                return []
            graficos = [{
                "tipo": "barras",
                "titulo": "Conversas por vendedor",
                "labels": [_primeiro_nome(v.get("nome")) for v in vs],
                "series": [{"nome": "Conversas", "dados": [v.get("conversas") or 0 for v in vs], "cor": "azul"}],
            }]
            com_tempo = [v for v in vs if v.get("resposta_media_min") is not None]
            if len(com_tempo) >= 2:
                graficos.append({
                    "tipo": "barras",
                    "titulo": "Tempo médio de resposta",
                    "sufixo": " min",
                    "labels": [_primeiro_nome(v.get("nome")) for v in com_tempo],
                    "series": [{
                        "nome": "Minutos",
                        "dados": [int(v["resposta_media_min"]) for v in com_tempo],
                        "cor": "ambar",
                    }],
                })
            return graficos

        if nome == "conversas_paradas":
            cs = [c for c in dados.get("conversas", []) if c.get("parada_dias") is not None]
            if not cs:
                return []
            cs = sorted(cs, key=lambda c: c["parada_dias"], reverse=True)[:10]
            # Escala pela maior barra: com tudo parado há poucas horas, um eixo
            # em dias vira "0, 1, 2" e não distingue nada.
            em_horas = max(c["parada_dias"] for c in cs) < 2
            dados_serie = [
                round(c["parada_dias"] * 24) if em_horas else c["parada_dias"] for c in cs
            ]
            return [{
                "tipo": "barras_h",
                "titulo": "Horas sem interação" if em_horas else "Dias sem interação",
                "sufixo": "h" if em_horas else " dias",
                "labels": [_primeiro_nome(c.get("nome_contato"), c.get("numero", "—")[-4:]) for c in cs],
                "series": [{"nome": "Horas" if em_horas else "Dias", "dados": dados_serie, "cor": "rosa"}],
            }]

        if nome == "timeline_conversa":
            msgs = dados.get("mensagens", [])
            if len(msgs) < 3:
                return []
            cliente = sum(1 for m in msgs if m.get("de") == "cliente")
            ia = sum(1 for m in msgs if m.get("de") == "ia")
            vendedor = len(msgs) - cliente - ia
            fatias = [("Cliente", cliente, "azul"), ("Vendedor", vendedor, "verde"), ("IA", ia, "violeta")]
            fatias = [f for f in fatias if f[1] > 0]
            if len(fatias) < 2:
                return []
            return [{
                "tipo": "rosca",
                "titulo": "Quem falou na conversa",
                "labels": [f[0] for f in fatias],
                "series": [{
                    "nome": "Mensagens",
                    "dados": [f[1] for f in fatias],
                    "cores": [f[2] for f in fatias],
                }],
            }]
    except Exception as e:
        logger.warning("[analista] falha ao montar gráfico de %s: %s", nome, e)
    return []


_TITULO_PADRAO = {
    "resumo": "Resumo da conversa",
    "coletado": "Informações coletadas",
    "interesse": "Interesse e chance de fechamento",
    "atencao": "Pontos de atenção",
    "proxima_acao": "Próxima ação recomendada",
}


def _montar_cards(conteudo: str | None, conversa: dict | None, timeline: dict | None) -> list[dict]:
    """Junta a visão geral (código) com os cards que o modelo escreveu.

    Descarta card vazio: a interface não deve mostrar caixa sem conteúdo — foi
    o pedido explícito de que "card sem informação útil não aparece".
    Se o JSON vier quebrado, devolve um card único com o texto cru; melhor
    mostrar a análise sem formatação do que engolir a resposta.
    """
    cards: list[dict] = []
    identidade = _identidade(conversa)

    visao = _card_visao_geral(conversa, timeline)
    if visao:
        cards.append(visao)

    bruto = (conteudo or "").strip()
    if not bruto:
        return cards

    try:
        dados = _ler_json(bruto)
        for c in dados.get("cards", []):
            tipo = c.get("tipo")
            if tipo not in _TITULO_PADRAO:
                continue
            itens = [i.strip() for i in (c.get("itens") or []) if isinstance(i, str) and i.strip()]
            campos = [
                {"rotulo": str(x.get("rotulo", "")).strip(), "valor": str(x.get("valor", "")).strip()}
                for x in (c.get("campos") or [])
                if str(x.get("valor", "")).strip()
            ]
            texto = (c.get("texto") or "").strip()
            if not (itens or campos or texto):
                continue

            # Título do resumo montado aqui, não pelo modelo: ele escrevia o
            # telefone no formato que tivesse visto ("+55 14 98138-6372",
            # "5514981386372") e às vezes omitia o nome. Nome e telefone são
            # fato — saem da conversa, com a máscara do país.
            titulo = (c.get("titulo") or "").strip() or _TITULO_PADRAO[tipo]
            if tipo == "resumo" and identidade:
                titulo = f"Resumo da conversa com {identidade}"

            cards.append({
                "tipo": tipo,
                "titulo": titulo,
                "nivel": c.get("nivel") if tipo in ("interesse", "atencao") else None,
                "texto": texto or None,
                "itens": itens,
                "campos": campos,
            })
    except Exception as e:
        # Nunca despejar o JSON cru na tela: quem lê não tem o que fazer com
        # `{"cards":[{"tipo":...`. Se nem o parser tolerante deu conta, é falha
        # nossa — assume isso e peça para repetir.
        logger.warning("[analista] resposta ilegível do modelo (%s): %r", e, bruto[:400])
        cards.append({
            "tipo": "atencao", "titulo": "Não consegui montar a resposta", "nivel": "media",
            "texto": "A análise voltou num formato que não consegui exibir. Tente perguntar de novo.",
            "itens": [], "campos": [],
        })

    return cards


def _ler_json(bruto: str) -> dict:
    """Lê o JSON da resposta tolerando lixo em volta.

    O modelo às vezes devolve DOIS objetos colados (`{...}{...}`) ou embrulha em
    cerca de markdown. `raw_decode` lê o primeiro valor válido e ignora o resto,
    em vez de derrubar a resposta inteira por causa do excedente.
    """
    texto = bruto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```[a-zA-Z]*\s*", "", texto)
        texto = re.sub(r"\s*```$", "", texto).strip()

    inicio = texto.find("{")
    if inicio < 0:
        raise ValueError("sem objeto JSON na resposta")

    dados, _ = json.JSONDecoder().raw_decode(texto[inicio:])
    if not isinstance(dados, dict):
        raise ValueError("JSON não é um objeto")
    return dados


def _cards_para_texto(cards: list[dict]) -> str:
    """Versão em markdown dos cards — usada como reserva pela interface."""
    partes: list[str] = []
    for c in cards:
        partes.append(f"**{c['titulo']}**")
        for campo in c.get("campos") or []:
            partes.append(f"- {campo['rotulo']}: {campo['valor']}")
        for item in c.get("itens") or []:
            partes.append(f"- {item}")
        if c.get("texto"):
            partes.append(c["texto"])
        partes.append("")
    return "\n".join(partes).strip() or "Não consegui montar uma resposta."


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

    # Data/hora atual no prompt: sem isso o modelo não tem como interpretar
    # "hoje", "ontem" ou "esta semana" — ele não conhece o relógio. Vai como
    # texto e não como ferramenta de propósito: é um dado fixo do turno, e uma
    # chamada extra só para perguntar as horas gastaria uma volta inteira.
    # Continua valendo que ele NÃO faz conta de data: quem mede quanto tempo
    # passou é o banco (ver os campos "..._ha").
    agora = datetime.now(FUSO_BR)
    contexto_tempo = (
        f"\n\nAGORA: {agora.strftime('%A, %d/%m/%Y às %H:%M')} (horário de Brasília). "
        "Use isto só para entender expressões como 'hoje', 'ontem' ou 'esta semana' "
        "e escolher o parâmetro `horas`. Para dizer há quanto tempo algo aconteceu, "
        "use sempre os campos já calculados."
    )
    mensagens: list[dict] = [{"role": "system", "content": SYSTEM + contexto_tempo}]
    for h in (historico or [])[-MAX_HISTORICO:]:
        papel = h.get("papel")
        texto = (h.get("texto") or "").strip()
        if papel in ("user", "assistant") and texto:
            mensagens.append({"role": papel, "content": texto[:4000]})
    mensagens.append({"role": "user", "content": pergunta})

    rastro: list[dict] = []
    cobertura: dict | None = None
    peso_cobertura = 0
    # Resultados já obtidos nesta pergunta, por (ferramenta + argumentos
    # normalizados). O modelo repete a mesma busca com o telefone em formatos
    # diferentes ("556291366367" e "55 62 9136-6367") — sem isto vira consulta
    # duplicada no banco e uma linha confusa no relatório.
    cache: dict[str, dict] = {}
    graficos: list[dict] = []
    vistos: set[tuple] = set()      # assinaturas dos gráficos já incluídos
    titulos_usados: list[str] = []  # títulos já na tela, para numerar repetidos
    # conversa_id -> dados da conversa, para nomear gráficos quando o mesmo
    # cliente tem mais de uma conversa (um canal por vendedor).
    conversas_vistas: dict[str, dict] = {}
    # Guardados para montar a visão geral por código (ver _card_visao_geral).
    conversa_ctx: dict | None = None
    timeline_ctx: dict | None = None

    try:
        for volta in range(MAX_VOLTAS):
            resp = await cliente.chat.completions.create(
                model=MODELO,
                messages=mensagens,
                tools=FERRAMENTAS,
                temperature=0.2,
                response_format=ESQUEMA_RESPOSTA,
            )
            escolha = resp.choices[0].message
            chamadas = escolha.tool_calls or []

            if not chamadas:
                await saldo.registrar_resultado_openai(usuario_id, sucesso=True)
                cards = _montar_cards(escolha.content, conversa_ctx, timeline_ctx)
                return {
                    # `resposta` continua sendo enviada: é o que aparece se a
                    # estruturação falhar, e o que versões antigas da interface
                    # sabem exibir.
                    "resposta": _cards_para_texto(cards),
                    "cards": cards,
                    "rastro": rastro,
                    "cobertura": cobertura,
                    "graficos": graficos,
                    "titulo": _titulo(pergunta),
                }

            mensagens.append({
                "role": "assistant",
                # `content` vai NULO de propósito quando há tool calls. Com saída
                # estruturada o modelo às vezes já manda um JSON junto da chamada
                # — uma resposta provisória, antes de ver o resultado. Guardar
                # isso no histórico fazia ele repetir o bloco no fim, e a
                # resposta final chegava com dois JSONs colados.
                "content": None,
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

                chave = _chave_cache(nome, args)
                if not fn:
                    dados = {"erro": f"ferramenta desconhecida: {nome}"}
                elif chave in cache:
                    dados = cache[chave]          # repetição: não vai ao banco de novo
                else:
                    try:
                        # usuario_id é injetado AQUI — o modelo não escolhe empresa.
                        dados = await fn(usuario_id=usuario_id, **args)
                        cache[chave] = dados
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
                        achado = _extrair_cobertura(nome, dados)
                        if achado and achado[0] >= peso_cobertura:
                            peso_cobertura, cobertura = achado
                        # Guarda as conversas encontradas para poder nomear os
                        # gráficos depois (ver o bloco de título abaixo).
                        if nome in ("buscar_conversa_por_telefone", "buscar_conversas"):
                            for c in dados.get("conversas") or []:
                                if c.get("id"):
                                    conversas_vistas[str(c["id"])] = c

                        # Só entra gráfico que ainda não existe. O cache impede
                        # a MESMA chamada de repetir, mas duas chamadas
                        # diferentes podem produzir o mesmo gráfico — pedir a
                        # timeline com `limite` distinto, por exemplo. Gráfico
                        # idêntico duas vezes é sempre defeito, nunca dado.
                        for g in _extrair_graficos(nome, dados):
                            # O MESMO cliente pode ter duas conversas (uma por
                            # canal/vendedor) e o modelo lê as duas. Sem o nome
                            # de quem é cada uma, saem dois gráficos com título
                            # igual e a tela parece estar repetindo o mesmo.
                            if nome == "timeline_conversa":
                                dona = conversas_vistas.get(str(args.get("conversa_id") or ""))
                                if dona:
                                    # Vendedor primeiro; se as duas conversas
                                    # forem do mesmo, o canal separa (é o que de
                                    # fato difere — uma conversa por instância).
                                    alvo = (dona.get("vendedor") or "").strip() or (dona.get("canal") or "").strip()
                                    if alvo:
                                        g["titulo"] = f"{g['titulo']} — {alvo}"

                            # 1) Descarta duplicata exata. A checagem vem ANTES
                            #    de qualquer renomeação: numerar primeiro faria
                            #    a cópia virar "título (2)" e escapar do filtro.
                            assinatura = (
                                g["tipo"], g["titulo"],
                                tuple(g["labels"]),
                                tuple(g["series"][0]["dados"]),
                            )
                            if assinatura in vistos:
                                continue
                            vistos.add(assinatura)

                            # 2) Título repetido com dados diferentes são dois
                            #    gráficos legítimos — numera para a tela não
                            #    mostrar dois blocos indistinguíveis.
                            base_titulo = g["titulo"]
                            repetidos = sum(1 for t in titulos_usados if t == base_titulo)
                            if repetidos:
                                g["titulo"] = f"{base_titulo} ({repetidos + 1})"
                            titulos_usados.append(base_titulo)

                            graficos.append(g)

                        # Contexto da visão geral. Só a PRIMEIRA conversa achada
                        # vira cabeçalho: se o modelo buscar outras depois, o
                        # card continua descrevendo o cliente da pergunta.
                        if nome == "buscar_conversa_por_telefone" and conversa_ctx is None:
                            achadas = dados.get("conversas") or []
                            if len(achadas) == 1:
                                conversa_ctx = achadas[0]
                        elif nome == "timeline_conversa" and timeline_ctx is None:
                            timeline_ctx = dados

                mensagens.append({
                    "role": "tool",
                    "tool_call_id": c.id,
                    "content": json.dumps(dados, ensure_ascii=False, default=str)[:24000],
                })

        # Estourou o teto de voltas: devolve o que der, sem travar o usuário.
        await saldo.registrar_resultado_openai(usuario_id, sucesso=True)
        return {
            "resposta": "A consulta ficou longa demais e parei no meio. Tente uma pergunta mais específica.",
            "cards": [],
            "rastro": rastro,
            "cobertura": cobertura,
            "graficos": graficos,
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
