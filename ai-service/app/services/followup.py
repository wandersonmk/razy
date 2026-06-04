"""Processador de follow-up automático.

Fluxo:
  1. Scheduler chama processar_followups_pendentes a cada 60s.
  2. Busca followup_disparos com status='pendente' e agendado_para <= now().
  3. Para cada: verifica se contato respondeu → cancela. Caso contrário, gera/envia a
     mensagem (IA ou manual), marca como 'enviado' e agenda a próxima etapa.
  4. Mantém o thread_id idêntico ao disparo original → contexto LangGraph preservado.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

from app.db.redis import get_redis
from app.graph.build import gerar_followup, registrar_no_contexto
from app.services import repo
from app.services.assistente import marcar_saida
from app.services.uazapi import enviar_texto

logger = logging.getLogger("uvicorn.error")

SYSTEM_PROMPT_FU = (
    "Você é um assistente de relacionamento. Escreva UMA mensagem curta de follow-up "
    "para um cliente que ainda não respondeu ao contato anterior. Seja cordial, natural e "
    "lembre levemente do assunto sem ser insistente. Máximo 2 frases. Português do Brasil. "
    "Responda apenas com o texto da mensagem, sem aspas nem assinaturas."
)


def _formatar_telefone(t: str) -> str:
    nums = re.sub(r"\D", "", t or "")
    if nums.startswith("55") and len(nums) >= 12:
        return nums
    if len(nums) in (10, 11):
        return "55" + nums
    return nums


def _interpolar(template: str, contato_nome: str, contato_tel: str, contato_obs: str) -> str:
    # Placeholders case-insensitive: {nome}, {Nome}, {NOME} etc. são equivalentes.
    valores = {
        "nome": contato_nome or "",
        "telefone": contato_tel or "",
        "observacao": contato_obs or "",
    }
    return re.sub(
        r"\{(\w+)\}",
        lambda m: valores.get(m.group(1).lower(), m.group(0)),
        template or "",
    )


def _thread_id(telefone: str, usuario_id: str, instancia_id: str) -> str:
    return f"{telefone}_{usuario_id}_{instancia_id}"


async def carregar_etapa1(campanha_id: str, usuario_id: str) -> tuple[dict | None, dict | None]:
    """Retorna (config, etapa1) do follow-up aplicável (específico da campanha ou
    global), ou (None, None) se não houver follow-up configurado/etapas."""
    config = await repo.get_followup_config_aplicavel(campanha_id, usuario_id)
    if not config:
        return None, None
    etapas = await repo.get_followup_etapas(config["id"])
    if not etapas:
        return None, None
    return config, etapas[0]


async def agendar_etapa1_contato(
    *,
    config: dict,
    etapa1: dict,
    campanha_id: str,
    usuario_id: str,
    contato_id: str,
    canal_id: str | None,
    base_dt: datetime | None = None,
) -> bool:
    """Agenda a etapa 1 do follow-up de UM contato, contando o tempo a partir de
    `base_dt` — por padrão AGORA, i.e., o instante em que o contato recebeu o
    disparo. Assim cada lead começa a contar o follow-up no seu próprio envio, sem
    depender do término da campanha (que pode levar dias). Idempotente: não
    reinscreve um contato que já está na sequência. Retorna True se inscreveu."""
    if not canal_id:
        return False
    base = base_dt or datetime.now(timezone.utc)
    agendado_para = base + timedelta(minutes=etapa1["delay_minutos"])
    return await repo.agendar_followup_etapa1_idempotente(
        config_id=config["id"],
        etapa_id=etapa1["id"],
        campanha_id=campanha_id,
        contato_id=contato_id,
        usuario_id=usuario_id,
        canal_id=canal_id,
        agendado_para=agendado_para,
    )


async def backfill_etapa1_enviados(
    *,
    config: dict,
    etapa1: dict,
    campanha_id: str,
    usuario_id: str,
    canal_fallback: str,
) -> int:
    """Garante que todo contato que JÁ recebeu o disparo (status=enviado) esteja
    inscrito na etapa 1 — contando o tempo a partir do envio real (`enviado_em`),
    então quem já passou do prazo dispara no próximo ciclo. Cobre a retomada de uma
    campanha e contatos enviados antes desta lógica existir. Idempotente."""
    enviados = await repo.get_disparos_enviados_para_followup(campanha_id)
    agendados = 0
    for d in enviados:
        novo = await agendar_etapa1_contato(
            config=config,
            etapa1=etapa1,
            campanha_id=campanha_id,
            usuario_id=usuario_id,
            contato_id=d["contato_id"],
            canal_id=d["canal_id"] or canal_fallback,
            base_dt=d["enviado_em"],
        )
        if novo:
            agendados += 1
    if agendados:
        tipo = "global" if config.get("campanha_id") is None else "específica"
        logger.info(
            "[followup] backfill: %d contato(s) já enviados inscritos na etapa 1 "
            "(campanha %s, config %s)",
            agendados, campanha_id, tipo,
        )
    return agendados


async def processar_followups_pendentes(app) -> None:
    """Processa todos os follow-ups vencidos em background."""
    pendentes = await repo.get_followup_pendentes()
    if not pendentes:
        return
    logger.info("[followup] processando %d follow-up(s) pendente(s)", len(pendentes))
    tasks = [asyncio.create_task(_processar_disparo(app, d)) for d in pendentes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            logger.exception("[followup] erro em disparo: %s", r)


async def _processar_disparo(app, d: dict) -> None:
    disparo_id = d["id"]

    # Se contato já respondeu à campanha original, marca e encerra.
    if await repo.contato_ja_respondeu(d["campanha_id"], d["contato_id"]):
        await repo.atualizar_followup_disparo(disparo_id, status="respondeu")
        logger.info("[followup] contato %s respondeu — encerrado", d["contato_id"])
        return

    telefone = _formatar_telefone(d["contato_telefone"] or "")
    if not telefone or len(telefone) < 10:
        await repo.atualizar_followup_disparo(disparo_id, status="cancelado")
        return

    tid = _thread_id(telefone, d["usuario_id"], d["canal_id"] or "")

    try:
        if d["etapa_modo"] == "ia":
            openai_key = await repo.get_openai_key(d["usuario_id"])
            # gerar_followup usa o histórico acumulado da thread (inclui mensagens
            # manuais já registradas) — a IA sempre parte do contexto da última mensagem.
            mensagem = await gerar_followup(
                app.state.graph,
                thread_id=tid,
                nome=d["contato_nome"] or "",
                observacao=d["contato_obs"] or "",
                etapa=int(d["etapa_ordem"]),
                api_key=openai_key,
            )
        else:
            mensagem = _interpolar(
                d["etapa_mensagem"] or "",
                d["contato_nome"] or "",
                d["contato_telefone"] or "",
                d["contato_obs"] or "",
            )

        resultado = await enviar_texto(token=d["canal_token"], numero=telefone, texto=mensagem)

        if resultado["sucesso"]:
            await repo.atualizar_followup_disparo(disparo_id, status="enviado", mensagem_enviada=mensagem)
            # Marca como nosso envio (evita auto-pausa pelo eco fromMe do follow-up).
            try:
                await marcar_saida(get_redis(), tid, mensagem)
            except Exception:
                pass
            # Registra no contexto da thread. IA já grava sozinha; manual precisa ser
            # anexado para que as próximas etapas de IA tenham o histórico completo.
            if d["etapa_modo"] != "ia":
                try:
                    await registrar_no_contexto(app.state.graph, thread_id=tid, texto=mensagem)
                except Exception as e:
                    logger.warning("[followup] falha ao registrar contexto manual (%s): %s", telefone, e)
            logger.info(
                "[followup] enviado para %s (etapa %d, campanha %s)",
                telefone, d["etapa_ordem"], d["campanha_id"],
            )
            # Agenda próxima etapa se existir.
            if d.get("next_etapa_id"):
                prox = datetime.now(timezone.utc) + timedelta(minutes=d["next_etapa_delay"])
                await repo.inserir_followup_disparo(
                    config_id=d["config_id"],
                    etapa_id=d["next_etapa_id"],
                    campanha_id=d["campanha_id"],
                    contato_id=d["contato_id"],
                    usuario_id=d["usuario_id"],
                    canal_id=d["canal_id"],
                    agendado_para=prox,
                )
        else:
            await repo.atualizar_followup_disparo(disparo_id, status="cancelado")
            logger.warning("[followup] falha ao enviar para %s — cancelado", telefone)

    except Exception as e:
        logger.exception("[followup] erro ao processar disparo %s: %s", disparo_id, e)
        await repo.atualizar_followup_disparo(disparo_id, status="cancelado")
