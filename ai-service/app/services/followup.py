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

from app.graph.build import gerar_mensagem
from app.services import repo
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
    return (
        (template or "")
        .replace("{nome}", contato_nome or "")
        .replace("{telefone}", contato_tel or "")
        .replace("{observacao}", contato_obs or "")
    )


def _thread_id(telefone: str, usuario_id: str, instancia_id: str) -> str:
    return f"{telefone}_{usuario_id}_{instancia_id}"


async def agendar_etapa1(
    *,
    app,
    campanha_id: str,
    usuario_id: str,
    canal_id: str,
    contatos_ids: list[str],
) -> None:
    """Chamado pelo orquestrador ao finalizar o disparo inicial: agenda o step 1."""
    if not contatos_ids:
        return
    config = await repo.get_followup_config_by_campanha(campanha_id)
    if not config:
        return
    etapas = await repo.get_followup_etapas(config["id"])
    if not etapas:
        return
    etapa1 = etapas[0]
    agendado_para = datetime.now(timezone.utc) + timedelta(minutes=etapa1["delay_minutos"])
    await repo.bulk_inserir_followup_disparos(
        config_id=config["id"],
        etapa_id=etapa1["id"],
        campanha_id=campanha_id,
        contato_ids=contatos_ids,
        usuario_id=usuario_id,
        canal_id=canal_id,
        agendado_para=agendado_para,
    )
    logger.info(
        "[followup] %d contatos agendados para etapa 1 (campanha %s, em %s min)",
        len(contatos_ids), campanha_id, etapa1["delay_minutos"],
    )


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
            mensagem = await gerar_mensagem(
                app.state.graph,
                thread_id=tid,
                nome=d["contato_nome"] or "",
                observacao=d["contato_obs"] or "",
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
