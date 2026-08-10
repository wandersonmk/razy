"""Orquestrador de disparo de campanha.

Roda em background: percorre os contatos do público da campanha, gera/monta a
mensagem (IA ou manual), envia pela UAzAPI, grava o disparo e atualiza os
contadores — respeitando o intervalo configurado entre os envios.

Seleção de canal — três modos (mutuamente exclusivos):
  • Canal único: usa só o canal vinculado à campanha.
  • Roteamento (usar_roteamento): failover. Usa um canal por vez; quando ele
    acumula THRESHOLD_BLOQUEIO falhas é considerado bloqueado e sai da rotação.
  • Alternância (alternar_canais): round-robin. Cada contato sai por um canal
    diferente, distribuindo a carga entre todos os conectados.

Em ambos os modos multi-canal, cada contato tem failover: se o canal escolhido
falhar no envio, o MESMO contato é tentado imediatamente no próximo canal
disponível antes de ser marcado como falha. Canais que acumulam o limite de
falhas saem da rotação e o evento é registrado nos logs da campanha.

Caso à parte: quando o WhatsApp devolve restrição temporária (erro 463), o canal
sai da rotação na PRIMEIRA recusa e recebe um cooldown gravado no banco
(instancias.bloqueado_ate), respeitado também pelas campanhas seguintes. A sessão
está conectada — quem bloqueou foi o WhatsApp —, então insistir só reforça a
restrição do número.
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.db.redis import get_redis
from app.graph.build import gerar_mensagem, registrar_no_contexto
from app.services import repo
from app.services.uazapi import enviar_texto, consultar_status
from app.services import followup as fu_service
from app.services.assistente import marcar_saida
from app.services.saldo import registrar_resultado_openai

logger = logging.getLogger("uvicorn.error")

# Falhas consecutivas no mesmo canal para considerá-lo bloqueado (sai da rotação).
THRESHOLD_BLOQUEIO = 3

# Cooldown gravado no banco quando o WhatsApp restringe a conta (erro 463).
# A restrição é temporária (horas a dias) e some sozinha quando o número reduz
# volume; 24h é o intervalo em que voltamos a testar o canal.
COOLDOWN_RESTRICAO_HORAS = 24

# Assinaturas do erro 463 da UAzAPI/WhatsApp: "the currently connected account is
# under a temporary restriction for starting new conversations, usually related to
# sending volume or quality". A sessão está CONECTADA — o bloqueio é do WhatsApp,
# então reler o QR Code não resolve e reenviar só piora a reputação do número.
_RESTRICAO_WHATSAPP = re.compile(
    r"(server error 463|temporary restriction|temporarily restricted)", re.IGNORECASE
)


def _e_restricao_whatsapp(erro: str | None) -> bool:
    return bool(erro and _RESTRICAO_WHATSAPP.search(erro))

# Exceções em que NÃO sabemos se a mensagem chegou a ser enviada: a requisição
# saiu (conexão ok) mas a UAzAPI não respondeu a tempo — ela pode ter recebido e
# ENTREGUE a mensagem, só demorou a responder. Reenviar por outro canal nesses
# casos DUPLICARIA a mensagem para o contato, então NÃO fazemos failover.
# Já erros de conexão (ConnectError/ConnectTimeout/Write*) garantem que nada foi
# enviado, então esses seguem com failover normal.
ENVIO_AMBIGUO = (httpx.ReadTimeout, httpx.ReadError, httpx.RemoteProtocolError)

# Mantém referência das tasks em andamento (evita coleta pelo GC).
_tasks: set[asyncio.Task] = set()


def thread_id_de(telefone: str, usuario_id: str, instancia_id: str) -> str:
    return f"{telefone}_{usuario_id}_{instancia_id}"


def _formatar_telefone(t: str) -> str:
    nums = re.sub(r"\D", "", t or "")
    if nums.startswith("55") and len(nums) >= 12:
        return nums
    if len(nums) in (10, 11):
        return "55" + nums
    return nums


def _interpolar(template: str, contato: dict) -> str:
    # Placeholders case-insensitive: {nome}, {Nome}, {NOME} etc. são equivalentes.
    valores = {
        "nome": contato.get("nome") or "",
        "telefone": contato.get("telefone") or "",
        "empresa": contato.get("empresa") or "",
        "observacao": contato.get("observacao") or "",
        "etapa": contato.get("etapa") or "",
    }
    return re.sub(
        r"\{(\w+)\}",
        lambda m: valores.get(m.group(1).lower(), m.group(0)),
        template or "",
    )


def _nome_canal(c: dict) -> str:
    return c.get("phone") or c.get("uazapi_instance_name") or str(c["id"])


def agendar_disparo(app, campanha_id: str) -> None:
    """Dispara a campanha em background (não bloqueia a resposta HTTP)."""
    task = asyncio.create_task(_disparar(app, campanha_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _log(campanha_id: str, usuario_id: str, nivel: str, evento: str,
               detalhe: str | None = None, canal_id: str | None = None) -> None:
    """Grava um evento no log da campanha (silencia erros para não derrubar o disparo)."""
    try:
        await repo.inserir_log_campanha(
            campanha_id=campanha_id, usuario_id=usuario_id,
            nivel=nivel, evento=evento, detalhe=detalhe, canal_id=canal_id,
        )
    except Exception as e:
        logger.warning("[log] falha ao gravar log da campanha %s: %s", campanha_id, e)


async def _log_resumo_canais(
    campanha_id: str,
    usuario_id: str,
    canais: list[dict],
    envios_ok: dict[str, int],
    falhas_tot: dict[str, int],
    ultimo_erro: dict[str, str],
    bloqueados: set[str],
    restritos: set[str],
) -> None:
    """Grava um panorama por canal no log da campanha.

    Destaca (nível "erro") os canais que foram tentados mas NÃO enviaram nada —
    tipicamente sessão caída/inválida na UAzAPI, mesmo com status "connected".
    Sem isso, o failover regrava o disparo no canal que funcionou e o canal
    quebrado some do painel (aparece como 0 enviados / 0 falhas). Só emite linha
    para canais que tiveram alguma falha — canais saudáveis não poluem o log.
    """
    for c in canais:
        cid = str(c["id"])
        falhas = falhas_tot.get(cid, 0)
        if falhas == 0:
            continue
        ok = envios_ok.get(cid, 0)
        nome = _nome_canal(c)
        motivo = ultimo_erro.get(cid) or "erro desconhecido"
        if cid in restritos:
            # Não é sessão caída: o WhatsApp restringiu a conta. Mandar reler o QR
            # aqui só desperdiça o tempo do operador (e não destrava nada).
            await _log(
                campanha_id, usuario_id, "aviso", "Canal em restrição do WhatsApp",
                detalhe=(
                    f"Canal {nome}: {ok} enviado(s), {falhas} falha(s). Fora do disparo por "
                    f"restrição temporária do WhatsApp para iniciar novas conversas (erro 463) — "
                    f"a sessão segue conectada. Reduza o volume deste número e aguarde o cooldown."
                ),
                canal_id=cid,
            )
        elif ok == 0:
            await _log(
                campanha_id, usuario_id, "erro", "Canal não enviou nada",
                detalhe=(
                    f"Canal {nome} NÃO enviou nenhuma mensagem ({falhas} falha(s)). "
                    f"Provável sessão desconectada/inválida na UAzAPI — reconecte "
                    f"(releia o QR Code) e teste um envio manual. Último erro: {motivo}"
                ),
                canal_id=cid,
            )
        else:
            estado = " (bloqueado na rotação)" if cid in bloqueados else ""
            await _log(
                campanha_id, usuario_id, "aviso", "Falhas no canal",
                detalhe=(
                    f"Canal {nome}{estado}: {ok} enviado(s), {falhas} falha(s). "
                    f"Último erro: {motivo}"
                ),
                canal_id=cid,
            )


async def _separar_em_cooldown(
    campanha_id: str,
    usuario_id: str,
    candidatos: list[dict],
) -> list[dict]:
    """Tira da rotação os canais em cooldown por restrição do WhatsApp (erro 463).

    O bloqueio vive no banco (`instancias.bloqueado_ate`) justamente porque o
    estado em memória morre com o disparo: sem isso, TODA campanha nova volta a
    tentar o número restrito, queima 3 contatos e ainda reforça a restrição.
    Registra no log da campanha quem ficou de fora e até quando.
    """
    agora = datetime.now(timezone.utc)
    liberados: list[dict] = []
    em_cooldown: list[str] = []
    for c in candidatos:
        ate = c.get("bloqueado_ate")
        if ate and ate > agora:
            em_cooldown.append(f"{_nome_canal(c)} (até {ate.strftime('%d/%m %H:%M')} UTC)")
        else:
            liberados.append(c)

    if em_cooldown:
        await _log(
            campanha_id, usuario_id, "aviso",
            f"{len(em_cooldown)} canal(is) em restrição temporária do WhatsApp",
            detalhe=(
                "O WhatsApp restringiu estas contas para INICIAR novas conversas "
                "(erro 463 — volume/qualidade). Elas seguem conectadas e respondendo "
                "conversas existentes, mas ficam fora do disparo até o fim do "
                "cooldown: " + ", ".join(em_cooldown) + ". "
                "Reler o QR Code NÃO resolve — o número precisa reduzir volume e "
                "aquecer antes de voltar a disparar."
            ),
        )
        logger.info(
            "[disparo] %d canal(is) fora por restrição do WhatsApp: %s",
            len(em_cooldown), ", ".join(em_cooldown),
        )
    return liberados


async def _filtrar_canais_ao_vivo(
    campanha_id: str,
    usuario_id: str,
    candidatos: list[dict],
    modo_nome: str,
) -> tuple[list[dict], list[str]]:
    """Valida cada canal candidato AO VIVO na UAzAPI e devolve só os conectados.

    - Consulta os candidatos em paralelo (uma vez, no início do disparo).
    - Cura o `status` no banco quando o estado ao vivo diverge do gravado — assim
      o canal-fantasma some das próximas montagens e o recém-conectado passa a
      constar como 'connected' sem depender de alguém abrir a tela de Canais.
    - Registra no log da campanha os canais deixados de fora (nível 'aviso'),
      para o painel mostrar QUAL número não entrou e por quê.

    Retorna (canais_conectados, nomes_descartados).
    """
    if not candidatos:
        return [], []

    resultados = await asyncio.gather(
        *(consultar_status(token=c["uazapi_token"]) for c in candidatos),
        return_exceptions=True,
    )

    conectados: list[dict] = []
    descartados: list[str] = []
    for canal, res in zip(candidatos, resultados):
        cid = str(canal["id"])
        nome = _nome_canal(canal)
        stored = str(canal.get("status") or "").lower()

        # Estado incerto (exceção no gather OU consulta inconclusiva: rede/UAzAPI
        # 5xx). NÃO derruba um canal que o banco dava como conectado por causa de
        # um soluço, e NÃO reescreve o banco (o estado real é desconhecido).
        if isinstance(res, Exception) or res.get("inconclusivo"):
            if stored == "connected":
                conectados.append(canal)
            else:
                descartados.append(nome)
            continue

        if res.get("conectado"):
            conectados.append(canal)
            if stored != "connected":
                try:
                    await repo.marcar_status_instancia(cid, "connected")
                except Exception as e:
                    logger.warning("[disparo] falha ao curar status do canal %s: %s", nome, e)
        else:
            # A UAzAPI AFIRMA que está fora (desconectado ou instância inexistente).
            descartados.append(nome)
            if stored != "disconnected":
                try:
                    await repo.marcar_status_instancia(cid, "disconnected")
                except Exception as e:
                    logger.warning("[disparo] falha ao curar status do canal %s: %s", nome, e)

    if descartados:
        await _log(
            campanha_id, usuario_id, "aviso",
            f"{len(descartados)} canal(is) fora do {modo_nome}",
            detalhe=(
                "Não estão conectados na UAzAPI neste momento e foram deixados de "
                "fora do roteamento: " + ", ".join(descartados) + ". "
                "Reconecte-os na tela de Canais (releia o QR Code)."
            ),
        )
        logger.info(
            "[disparo] %d canal(is) descartado(s) por não estarem conectados ao vivo: %s",
            len(descartados), ", ".join(descartados),
        )
    return conectados, descartados


def _filtrar_escolhidos(candidatos: list[dict], canais_ids) -> list[dict]:
    """Mantém só os canais que a campanha escolheu, preservando a ordem original.

    Normaliza para texto minúsculo porque os dois lados podem chegar como UUID do
    asyncpg OU como string (lista vinda por JSON/PostgREST) — e um UUID textual em
    maiúsculas continua sendo o mesmo canal. Lista vazia nunca chega aqui: quem
    chama trata "sem escolha = todos" antes.
    """
    escolhidos = {str(x).lower() for x in canais_ids}
    return [c for c in candidatos if str(c["id"]).lower() in escolhidos]


async def _disparar(app, campanha_id: str) -> None:
    try:
        campanha = await repo.get_campanha(campanha_id)
        if not campanha:
            logger.error("[disparo] campanha %s não encontrada", campanha_id)
            return

        usar_roteamento = bool(campanha.get("usar_roteamento"))
        alternar = bool(campanha.get("alternar_canais"))
        multi = usar_roteamento or alternar

        if not multi and not campanha.get("canal_id"):
            logger.error("[disparo] campanha %s sem canal vinculado", campanha_id)
            return

        # Claim atômico: evita disparo duplicado (clique duplo / múltiplos workers).
        # `meu_token` (iniciado_em deste claim) identifica ESTE loop como dono da
        # campanha; se um disparo mais novo assumir, o token muda e este loop encerra.
        meu_token = await repo.claim_campanha(campanha_id)
        if meu_token is None:
            logger.warning("[disparo] campanha %s já reivindicada — ignorando", campanha_id)
            return

        usuario_id = campanha["usuario_id"]
        uid = str(usuario_id)

        # ── Montar lista de canais ──────────────────────────────────────────
        if multi:
            modo_nome = "alternância" if alternar else "roteamento"
            candidatos = await repo.get_canais_para_disparo(usuario_id)
            candidatos = [c for c in candidatos if c.get("uazapi_token")]
            # Canais ESCOLHIDOS na campanha. Lista vazia/NULL = todos os elegíveis
            # (comportamento histórico — campanhas antigas caem aqui). O filtro vem
            # antes do cooldown e da checagem ao vivo para não gastar chamada à
            # UAzAPI com canal que o dono nem quis usar.
            escolhidos = campanha.get("canais_ids") or []
            if escolhidos:
                candidatos = _filtrar_escolhidos(candidatos, escolhidos)
                if not candidatos:
                    msg = "Nenhum dos canais escolhidos está disponível para o disparo"
                    logger.error("[disparo] %s (campanha %s)", msg, campanha_id)
                    await _log(
                        campanha_id, uid, "erro", msg,
                        detalhe=(
                            f"{len(escolhidos)} canal(is) foram selecionados nesta campanha, mas nenhum "
                            "deles existe mais, tem token válido ou está fora do uso exclusivo de "
                            "notificação. Edite a campanha e escolha outros canais."
                        ),
                    )
                    await repo.atualizar_status_campanha(campanha_id, "falhou")
                    return
            # Cooldown por restrição do WhatsApp (erro 463): sai antes da consulta
            # ao vivo porque a UAzAPI daria o canal como conectado — o bloqueio é
            # do WhatsApp, não da sessão.
            candidatos = await _separar_em_cooldown(campanha_id, uid, candidatos)
            # Validação AO VIVO na UAzAPI: só entra no roteamento o canal REALMENTE
            # conectado agora. Evita canal-fantasma (excluído no painel da UAzAPI,
            # mas ainda 'connected' no banco) e inclui número recém-conectado cujo
            # status no banco ainda não sincronizou. Ver uazapi.consultar_status.
            canais, descartados = await _filtrar_canais_ao_vivo(
                campanha_id, uid, candidatos, modo_nome,
            )
            if not canais:
                msg = f"Nenhum canal conectado disponível para {modo_nome}"
                logger.error("[disparo] %s (campanha %s)", msg, campanha_id)
                detalhe = None
                if descartados:
                    detalhe = (
                        "Canais fora da rotação (não conectados na UAzAPI agora): "
                        + ", ".join(descartados)
                        + ". Reconecte-os na tela de Canais (releia o QR Code)."
                    )
                await _log(campanha_id, uid, "erro", msg, detalhe=detalhe)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return
            estrategia = "alternância (round-robin)" if alternar else "roteamento (failover)"
            escopo = f" entre os {len(escolhidos)} canal(is) escolhidos" if escolhidos else ""
            await _log(
                campanha_id, uid, "info",
                f"{estrategia.capitalize()}{escopo} — {len(canais)} canal(is) conectado(s)",
                detalhe=", ".join(_nome_canal(c) for c in canais),
            )
            if len(canais) < 2:
                await _log(
                    campanha_id, uid, "aviso",
                    "Apenas 1 canal conectado no momento do disparo — operando sem distribuição",
                    canal_id=str(canais[0]["id"]),
                )
        else:
            instancia = await repo.get_instancia(campanha["canal_id"])
            if not instancia or not instancia.get("uazapi_token"):
                logger.error("[disparo] instância/token indisponível para campanha %s", campanha_id)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return
            canais = [instancia]

        contatos = await repo.get_contatos_do_publico(campanha["publico_id"])
        if not contatos:
            logger.warning("[disparo] público sem contatos (campanha %s)", campanha_id)
            await repo.atualizar_status_campanha(campanha_id, "concluida")
            return

        ja_enviados = await repo.get_contatos_ja_enviados(campanha_id)

        # ── Follow-up por contato ───────────────────────────────────────────
        # O tempo do follow-up de cada lead conta a partir do MOMENTO em que ele
        # recebe o disparo — não do término da campanha (que pode levar dias).
        # Carrega a etapa 1 aplicável uma vez; o agendamento real é por contato.
        fu_config, fu_etapa1 = await fu_service.carregar_etapa1(campanha_id, uid)
        if fu_etapa1:
            try:
                # Retomada/legado: inscreve quem já recebeu (conta do enviado_em real).
                await fu_service.backfill_etapa1_enviados(
                    config=fu_config, etapa1=fu_etapa1,
                    campanha_id=campanha_id, usuario_id=uid,
                    canal_fallback=str(canais[0]["id"]),
                )
            except Exception as e:
                logger.warning("[disparo] erro no backfill de follow-up (não crítico): %s", e)

        modo = campanha.get("modo_mensagem") or "manual"
        intervalo = max(1, int(campanha.get("intervalo_segundos") or 10))
        graph = app.state.graph
        redis = get_redis()

        # Chave OpenAI: obrigatória para modo IA — vem do painel (Configurações → Integrações)
        openai_key: str | None = None
        if modo == "ia":
            from app.config import get_settings
            openai_key = await repo.get_openai_key(uid) or get_settings().OPENAI_API_KEY
            if not openai_key:
                msg = "Chave OpenAI não configurada. Acesse Configurações → Integrações e informe sua chave."
                logger.error("[disparo] %s (campanha %s, usuário %s)", msg, campanha_id, usuario_id)
                await _log(campanha_id, uid, "erro", "Chave OpenAI ausente", detalhe=msg)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return

        # ── Estado de seleção de canal ──────────────────────────────────────
        # falhas_por_canal: id -> falhas consecutivas; ao atingir o limite o canal
        # é considerado bloqueado e removido de `canais_disp()`.
        falhas_por_canal: dict[str, int] = {}
        # Métricas por canal (visibilidade no painel): totais acumulados na
        # campanha inteira — diferente de falhas_por_canal, que é consecutiva e
        # zera a cada sucesso. Usados no resumo final p/ expor canais quebrados
        # que, por causa do failover, sumiriam do painel (aparecem como 0/0).
        envios_ok_canal: dict[str, int] = {}
        falhas_tot_canal: dict[str, int] = {}
        ultimo_erro_canal: dict[str, str] = {}
        canais_bloqueados: set[str] = set()
        # Canais que saíram por restrição do WhatsApp (463), não por falha de
        # sessão: têm cooldown gravado no banco e mensagem própria no resumo.
        canais_restritos: set[str] = set()
        rr = 0          # ponteiro round-robin (modo alternância)
        ultimo_canal = canais[0]   # último canal que enviou com sucesso (p/ follow-up)

        def canais_disp() -> list[dict]:
            return [c for c in canais if falhas_por_canal.get(str(c["id"]), 0) < THRESHOLD_BLOQUEIO]

        if alternar:
            estrategia_label = "alternância"
        elif usar_roteamento:
            estrategia_label = "roteamento"
        else:
            estrategia_label = "canal único"

        retomada = len(ja_enviados) > 0
        await _log(
            campanha_id, uid, "info",
            "Retomada após falha" if retomada else "Disparo iniciado",
            detalhe=(
                f"{len(contatos)} contatos | {len(ja_enviados)} já enviados (ignorados) | "
                f"modo={modo} | intervalo={intervalo}s | estratégia={estrategia_label}"
            ) if retomada else (
                f"{len(contatos)} contatos | modo={modo} | intervalo={intervalo}s | estratégia={estrategia_label}"
            ),
            canal_id=str(canais[0]["id"]),
        )
        logger.info(
            "[disparo] iniciando campanha %s (%d contatos, modo=%s, intervalo=%ds, estrategia=%s, canais=%d)",
            campanha_id, len(contatos), modo, intervalo, estrategia_label, len(canais),
        )

        enviados = 0
        falhas = 0
        pausado = False

        for i, contato in enumerate(contatos):
            estado = await repo.get_estado_disparo(campanha_id)

            # Troca de dono: um disparo mais novo assumiu a campanha (ex.: pausa
            # seguida de retomada enquanto este loop ainda dormia). Encerra ESTE
            # loop sem alterar status — quem manda agora é o disparo novo.
            if estado is None or estado.get("iniciado_em") != meu_token:
                logger.warning(
                    "[disparo] campanha %s assumida por outro disparo — encerrando loop antigo",
                    campanha_id,
                )
                return

            # Pausa detectada pelo painel
            if estado.get("status") == "pausada":
                pausado = True
                logger.info("[disparo] campanha %s pausada — interrompendo", campanha_id)
                await _log(campanha_id, uid, "aviso", "Campanha pausada pelo usuário")
                break

            # Retomada: pula quem já recebeu
            if str(contato["id"]) in ja_enviados:
                continue

            # Canais ainda disponíveis neste momento
            disp = canais_disp()
            if not disp:
                msg = "Todos os canais foram bloqueados — campanha interrompida"
                logger.error("[disparo] %s (campanha %s)", msg, campanha_id)
                await _log(campanha_id, uid, "erro", msg)
                await repo.atualizar_status_campanha(campanha_id, "falhou")
                return

            telefone = _formatar_telefone(contato.get("telefone") or "")
            if not telefone or len(telefone) < 10:
                await repo.inserir_disparo(
                    campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                    status="falhou", mensagem_enviada=None, erro="Telefone inválido",
                )
                await repo.incrementar_contadores(campanha_id, falhas=1)
                falhas += 1
                continue

            # ── Ordem de tentativa de canais para ESTE contato ───────────────
            # Alternância: começa pelo próximo do round-robin; demais como fallback.
            # Roteamento/único: começa pelo primeiro disponível; demais como fallback.
            if alternar:
                inicio = disp[rr % len(disp)]
                rr += 1
            else:
                inicio = disp[0]
            ordem = [inicio] + [c for c in disp if str(c["id"]) != str(inicio["id"])]

            # Gera a mensagem uma única vez (reutilizada caso haja failover de canal).
            tid_inicial = thread_id_de(telefone, uid, str(inicio["id"]))
            try:
                if modo == "ia":
                    mensagem = await gerar_mensagem(
                        graph, thread_id=tid_inicial,
                        nome=contato.get("nome") or "",
                        observacao=contato.get("observacao") or "",
                        api_key=openai_key,
                    )
                    await registrar_resultado_openai(uid, sucesso=True)
                else:
                    mensagem = _interpolar(campanha.get("mensagem") or "", contato)
            except Exception as e:
                if modo == "ia":
                    await registrar_resultado_openai(uid, sucesso=False, erro=e)
                logger.exception("[disparo] erro ao gerar mensagem p/ %s: %s", telefone, e)
                await repo.inserir_disparo(
                    campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                    status="falhou", mensagem_enviada=None, erro=str(e)[:500],
                )
                await repo.incrementar_contadores(campanha_id, falhas=1)
                falhas += 1
                if i < len(contatos) - 1:
                    await asyncio.sleep(intervalo)
                continue

            # ── Tentativa de envio com failover por canal ────────────────────
            enviado_ok = False
            canal_usado = inicio
            ultimo_erro = None
            envio_incerto = False  # timeout de leitura: pode ter entregue → não reenviar
            for canal_try in ordem:
                cid = str(canal_try["id"])
                if falhas_por_canal.get(cid, 0) >= THRESHOLD_BLOQUEIO:
                    continue  # já bloqueado
                t0 = time.monotonic()
                try:
                    resultado = await enviar_texto(
                        token=canal_try["uazapi_token"], numero=telefone, texto=mensagem,
                    )
                    dur = time.monotonic() - t0
                    if resultado["sucesso"]:
                        enviado_ok = True
                        canal_usado = canal_try
                        falhas_por_canal[cid] = 0
                        envios_ok_canal[cid] = envios_ok_canal.get(cid, 0) + 1
                        # Voltou a enviar: se carregava cooldown vencido, libera o canal.
                        if canal_try.get("bloqueado_ate"):
                            canal_try["bloqueado_ate"] = None
                            try:
                                await repo.liberar_instancia(cid)
                            except Exception as e:
                                logger.warning(
                                    "[disparo] falha ao liberar cooldown do canal %s: %s",
                                    _nome_canal(canal_try), e,
                                )
                        logger.info(
                            "[disparo] enviado via canal %s em %.1fs", _nome_canal(canal_try), dur,
                        )
                        break
                    # A UAzAPI respondeu, mas recusou o envio (token inválido, número, etc.)
                    ultimo_erro = resultado.get("erro") or f"HTTP {resultado.get('status_code')}"
                    logger.warning(
                        "[disparo] envio recusado pelo canal %s (%.1fs): %s",
                        _nome_canal(canal_try), dur, ultimo_erro,
                    )
                    falhas_por_canal[cid] = falhas_por_canal.get(cid, 0) + 1
                    falhas_tot_canal[cid] = falhas_tot_canal.get(cid, 0) + 1
                    ultimo_erro_canal[cid] = ultimo_erro

                except Exception as e:
                    # Erro de rede/timeout: str(e) costuma vir vazio (ex.: ReadTimeout),
                    # então registramos o TIPO da exceção, que é o que de fato diagnostica.
                    dur = time.monotonic() - t0
                    ultimo_erro = type(e).__name__ + (f": {e}" if str(e) else "")
                    falhas_por_canal[cid] = falhas_por_canal.get(cid, 0) + 1
                    falhas_tot_canal[cid] = falhas_tot_canal.get(cid, 0) + 1
                    ultimo_erro_canal[cid] = ultimo_erro
                    if isinstance(e, ENVIO_AMBIGUO):
                        # Pode ter sido entregue — não refazer em outro canal (evita duplicar).
                        envio_incerto = True
                        logger.warning(
                            "[disparo] envio INCERTO via canal %s (%.1fs): %s — sem reenvio p/ não duplicar",
                            _nome_canal(canal_try), dur, type(e).__name__,
                        )
                    else:
                        logger.warning(
                            "[disparo] erro ao enviar via canal %s (%.1fs): %s",
                            _nome_canal(canal_try), dur, ultimo_erro,
                        )

                # Restrição do WhatsApp (463): sai da rotação JÁ nesta primeira
                # recusa e ganha cooldown no banco (vale para as próximas campanhas).
                # Não adianta gastar mais contatos — a conta não pode iniciar
                # conversa nova, e cada tentativa recusada reforça a restrição.
                if _e_restricao_whatsapp(ultimo_erro_canal.get(cid)) and cid not in canais_restritos:
                    canais_restritos.add(cid)
                    canais_bloqueados.add(cid)
                    falhas_por_canal[cid] = THRESHOLD_BLOQUEIO
                    ate = datetime.now(timezone.utc) + timedelta(hours=COOLDOWN_RESTRICAO_HORAS)
                    try:
                        await repo.bloquear_instancia_ate(cid, ate, ultimo_erro_canal[cid])
                    except Exception as e:
                        logger.warning(
                            "[disparo] falha ao gravar cooldown do canal %s: %s",
                            _nome_canal(canal_try), e,
                        )
                    aviso = (
                        f"Canal {_nome_canal(canal_try)} está sob restrição temporária do "
                        f"WhatsApp para iniciar novas conversas (erro 463). Ele continua "
                        f"conectado e respondendo conversas existentes, mas saiu do disparo "
                        f"por {COOLDOWN_RESTRICAO_HORAS}h (até {ate.strftime('%d/%m %H:%M')} UTC) "
                        f"— {len(canais_disp())} canal(is) restante(s). Reler o QR Code NÃO "
                        f"resolve: o número precisa reduzir volume e aquecer antes de voltar."
                    )
                    logger.warning("[disparo] %s", aviso)
                    await _log(campanha_id, uid, "aviso", "Canal em restrição do WhatsApp",
                               detalhe=aviso, canal_id=cid)

                # Canal atingiu o limite → bloqueado, registra e segue para o próximo
                # (restrição do WhatsApp já registrou aviso próprio acima).
                elif falhas_por_canal[cid] >= THRESHOLD_BLOQUEIO and cid not in canais_restritos:
                    canais_bloqueados.add(cid)
                    restantes = len(canais_disp())
                    motivo = ultimo_erro_canal.get(cid) or ultimo_erro or "erro desconhecido"
                    aviso = (
                        f"Canal {_nome_canal(canal_try)} atingiu {THRESHOLD_BLOQUEIO} falhas — "
                        f"removido da rotação ({restantes} canal(is) restante(s)). "
                        f"Último erro: {motivo}"
                    )
                    logger.warning("[disparo] %s", aviso)
                    await _log(campanha_id, uid, "aviso", "Canal bloqueado",
                               detalhe=aviso, canal_id=cid)

                # Envio incerto (timeout de leitura): interrompe o failover deste contato
                # para não arriscar entrega duplicada por outro número.
                if envio_incerto:
                    break

                # Em canal único não há failover.
                if not multi:
                    break

            instancia_id = canal_usado["id"]
            tid = thread_id_de(telefone, uid, str(instancia_id))

            if enviado_ok:
                erro_disparo = None
            elif envio_incerto:
                erro_disparo = f"Envio incerto (timeout, possível entrega) — não reenviado: {ultimo_erro}"
            else:
                erro_disparo = ultimo_erro or "Falha desconhecida no envio"

            await repo.inserir_disparo(
                campanha_id=campanha_id, contato_id=contato["id"], usuario_id=usuario_id,
                status="enviado" if enviado_ok else "falhou",
                mensagem_enviada=mensagem if enviado_ok else None,
                erro=erro_disparo,
                canal_id=str(instancia_id),
            )

            if enviado_ok:
                enviados += 1
                ultimo_canal = canal_usado
                await repo.incrementar_contadores(campanha_id, enviados=1)
                # Follow-up: o timer deste lead começa AGORA (quando ele recebeu),
                # independente de a campanha ainda estar em andamento ou ser pausada.
                if fu_etapa1:
                    try:
                        await fu_service.agendar_etapa1_contato(
                            config=fu_config, etapa1=fu_etapa1,
                            campanha_id=campanha_id, usuario_id=uid,
                            contato_id=str(contato["id"]), canal_id=str(instancia_id),
                        )
                    except Exception as e:
                        logger.warning("[disparo] erro ao agendar follow-up do contato (não crítico): %s", e)
                # Salva contexto no canal que de fato enviou (p/ o webhook resolver a resposta).
                try:
                    await redis.set(
                        f"conv:{tid}",
                        json.dumps({
                            "campanha_id": str(campanha_id),
                            "contato_id": str(contato["id"]),
                            "usuario_id": uid,
                            "instancia_id": str(instancia_id),
                            "telefone": telefone,
                        }),
                        ex=60 * 60 * 24 * 30,
                    )
                except Exception as e:
                    logger.warning("[disparo] envio OK mas falhou ao salvar contexto (%s): %s", telefone, e)
                # Marca como nosso envio (evita auto-pausa pelo eco fromMe do disparo).
                await marcar_saida(redis, tid, mensagem)
                # Garante que a thread do canal que DE FATO enviou tenha a mensagem no
                # histórico (essencial p/ follow-ups de IA e p/ resolver a resposta do
                # cliente). Casos:
                #  • manual: a IA não gravou nada → registra sempre.
                #  • IA com failover (tid != tid_inicial): a IA gravou na thread do canal
                #    inicial, que não foi o usado → registra na thread correta.
                #  • IA sem failover: gerar_mensagem já gravou na thread certa → nada a fazer.
                if modo != "ia" or tid != tid_inicial:
                    try:
                        await registrar_no_contexto(graph, thread_id=tid, texto=mensagem)
                    except Exception as e:
                        logger.warning("[disparo] falha ao registrar contexto (%s): %s", telefone, e)
            else:
                falhas += 1
                await repo.incrementar_contadores(campanha_id, falhas=1)

            # Intervalo entre disparos (não dorme depois do último)
            if i < len(contatos) - 1:
                await asyncio.sleep(intervalo)

        # Panorama por canal: expõe no painel canais que falharam/quebraram
        # (roda tanto na pausa quanto na conclusão).
        await _log_resumo_canais(
            campanha_id, uid, canais,
            envios_ok_canal, falhas_tot_canal, ultimo_erro_canal, canais_bloqueados,
            canais_restritos,
        )

        if pausado:
            logger.info(
                "[disparo] campanha %s interrompida (pausada): %d enviados, %d falhas nesta rodada",
                campanha_id, enviados, falhas,
            )
            return

        final = "falhou" if (enviados == 0 and falhas > 0) else "concluida"
        await repo.atualizar_status_campanha(campanha_id, final)

        # Safety-net: garante o follow-up agendado para todos que receberam
        # (idempotente; cobre algum agendamento por-contato que tenha falhado).
        if fu_etapa1:
            try:
                await fu_service.backfill_etapa1_enviados(
                    config=fu_config, etapa1=fu_etapa1,
                    campanha_id=campanha_id, usuario_id=uid,
                    canal_fallback=str(ultimo_canal["id"]),
                )
            except Exception as e:
                logger.warning("[disparo] erro ao agendar follow-up final (não crítico): %s", e)

        ativos = len(canais_disp())
        await _log(
            campanha_id, uid, "info", "Disparo concluído",
            detalhe=f"{enviados} enviados | {falhas} falhas | {ativos}/{len(canais)} canal(is) ativo(s) ao final",
            canal_id=str(ultimo_canal["id"]),
        )
        logger.info(
            "[disparo] campanha %s finalizada: %d enviados, %d falhas",
            campanha_id, enviados, falhas,
        )

    except Exception as e:
        logger.exception("[disparo] erro fatal na campanha %s: %s", campanha_id, e)
        try:
            await repo.atualizar_status_campanha(campanha_id, "falhou")
        except Exception:
            pass
