"""Acesso aos dados de negócio no Supabase (contatos, campanhas, disparos, instâncias).

O serviço conecta como o papel `postgres` (bypassa RLS), pois é um worker
de backend confiável. As queries são parametrizadas.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from app.db.supabase import get_supabase_pool


def _now() -> datetime:
    return datetime.now(timezone.utc)


@asynccontextmanager
async def advisory_lock(key: int):
    """Lock global (por sessão) no Postgres do Supabase.

    Garante que apenas UM worker rode uma tarefa de background por vez — sem isso,
    com `--workers 2` cada worker dispara seu próprio loop e processa os mesmos
    follow-ups, enviando em duplicidade. Yields True se obteve o lock, False se
    outro worker já o tem. Usa conexão dedicada (o lock é por sessão) e libera ao sair.
    """
    pool = get_supabase_pool()
    async with pool.acquire() as conn:
        got = bool(await conn.fetchval("select pg_try_advisory_lock($1)", key))
        try:
            yield got
        finally:
            if got:
                await conn.fetchval("select pg_advisory_unlock($1)", key)


# ── Leitura ──────────────────────────────────────────────────────────────────

async def get_campanha(campanha_id: str) -> dict | None:
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select id, usuario_id, publico_id, canal_id, nome, mensagem,
               modo_mensagem, intervalo_segundos, status,
               total_enviados, total_falhas, total_respostas,
               usar_roteamento, alternar_canais, canais_ids
        from public.campanhas
        where id = $1
        """,
        campanha_id,
    )
    return dict(row) if row else None


async def get_instancia(instancia_id: str) -> dict | None:
    """Busca a instância (canal) pelo id — fonte do token, número e instance name."""
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select id, usuario_id, uazapi_instance_name, uazapi_token, phone, status
        from public.instancias
        where id = $1
        """,
        instancia_id,
    )
    return dict(row) if row else None


async def get_instancia_by_token(token: str) -> dict | None:
    """Busca a instância pelo uazapi_token — usado para resolver o webhook.

    Traz `uso_notificacao` para o webhook respeitar o canal exclusivo de
    notificação de atendentes (esse número não atende cliente nem responde IA).
    """
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select id, usuario_id, uazapi_instance_name, uazapi_token, phone, status,
               coalesce(uso_notificacao, false) as uso_notificacao
        from public.instancias
        where uazapi_token = $1
        """,
        token,
    )
    return dict(row) if row else None


async def get_contatos_do_publico(publico_id: str) -> list[dict]:
    pool = get_supabase_pool()
    rows = await pool.fetch(
        """
        select id, nome, telefone, email, empresa, etapa, observacao
        from public.contatos
        where publico_id = $1
        order by created_at asc
        """,
        publico_id,
    )
    return [dict(r) for r in rows]


# ── Escrita ──────────────────────────────────────────────────────────────────

async def inserir_disparo(
    *,
    campanha_id: str,
    contato_id: str,
    usuario_id: str,
    status: str,                 # 'enviado' | 'falhou'
    mensagem_enviada: str | None,
    erro: str | None = None,
    canal_id: str | None = None,
) -> str:
    """Registra um disparo e retorna o id criado."""
    pool = get_supabase_pool()
    enviado_em = _now() if status == "enviado" else None
    row = await pool.fetchrow(
        """
        insert into public.disparos
            (campanha_id, contato_id, usuario_id, status, mensagem_enviada, erro, enviado_em, canal_id)
        values ($1, $2, $3, $4, $5, $6, $7, $8)
        returning id
        """,
        campanha_id, contato_id, usuario_id, status, mensagem_enviada, erro, enviado_em, canal_id,
    )
    return str(row["id"])


async def set_openai_sem_saldo(usuario_id: str, sem_saldo: bool) -> None:
    """Marca/limpa a flag de saldo OpenAI do usuário (alimenta o banner do painel).

    Escreve apenas quando o valor MUDA (`is distinct from`) — como isto é chamado
    a cada resposta da IA (webhook), evita um UPDATE inútil por mensagem.
    - sem_saldo=True  → upsert (garante a linha mesmo se o usuário usa a chave .env).
    - sem_saldo=False → só UPDATE (não cria linha-lixo para quem não tem integração).
    """
    pool = get_supabase_pool()
    if sem_saldo:
        await pool.execute(
            """
            insert into public.integracoes (usuario_id, openai_sem_saldo, openai_sem_saldo_em)
            values ($1, true, now())
            on conflict (usuario_id) do update
               set openai_sem_saldo = true, openai_sem_saldo_em = now()
             where public.integracoes.openai_sem_saldo is distinct from true
            """,
            usuario_id,
        )
    else:
        await pool.execute(
            """
            update public.integracoes
               set openai_sem_saldo = false, openai_sem_saldo_em = null
             where usuario_id = $1 and openai_sem_saldo is distinct from false
            """,
            usuario_id,
        )


async def incrementar_contadores(campanha_id: str, *, enviados: int = 0, falhas: int = 0) -> None:
    pool = get_supabase_pool()
    await pool.execute(
        """
        update public.campanhas
        set total_enviados = total_enviados + $2,
            total_falhas   = total_falhas + $3
        where id = $1
        """,
        campanha_id, enviados, falhas,
    )


async def incrementar_respostas(campanha_id: str, *, n: int = 1) -> None:
    pool = get_supabase_pool()
    await pool.execute(
        "update public.campanhas set total_respostas = total_respostas + $2 where id = $1",
        campanha_id, n,
    )


async def atualizar_status_campanha(campanha_id: str, status: str) -> None:
    """status: rascunho | em_andamento | concluida | pausada | falhou."""
    pool = get_supabase_pool()
    if status == "em_andamento":
        await pool.execute(
            "update public.campanhas set status = $2, iniciado_em = $3 where id = $1",
            campanha_id, status, _now(),
        )
    elif status in ("concluida", "falhou"):
        await pool.execute(
            "update public.campanhas set status = $2, concluido_em = $3 where id = $1",
            campanha_id, status, _now(),
        )
    else:
        await pool.execute(
            "update public.campanhas set status = $2 where id = $1",
            campanha_id, status,
        )


async def claim_campanha(campanha_id: str) -> datetime | None:
    """Marca a campanha como em_andamento de forma atômica.

    Retorna o TOKEN do disparo (o `iniciado_em` gravado neste claim) se ESTE
    processo conseguiu o claim, ou None caso contrário. O token muda a cada
    claim, então o loop o usa para detectar se foi substituído por um disparo
    mais novo (corrida pausa→retoma) e encerrar — evita disparo duplicado.
    """
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        update public.campanhas
        set status = 'em_andamento', iniciado_em = $2
        where id = $1 and status in ('rascunho', 'pausada', 'falhou')
        returning iniciado_em
        """,
        campanha_id, _now(),
    )
    return row["iniciado_em"] if row else None


async def get_campanha_status(campanha_id: str) -> str | None:
    """Leitura leve do status (usada para detectar pausa durante o disparo)."""
    pool = get_supabase_pool()
    row = await pool.fetchrow("select status from public.campanhas where id = $1", campanha_id)
    return row["status"] if row else None


async def get_estado_disparo(campanha_id: str) -> dict | None:
    """status + iniciado_em (token do disparo dono). Usado a cada iteração para
    detectar pausa E troca de dono (um disparo mais novo assumiu a campanha)."""
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        "select status, iniciado_em from public.campanhas where id = $1", campanha_id
    )
    return dict(row) if row else None


async def get_contatos_ja_enviados(campanha_id: str) -> set[str]:
    """IDs de contatos que já receberam (status enviado) — para retomar sem reenviar."""
    pool = get_supabase_pool()
    rows = await pool.fetch(
        "select contato_id from public.disparos where campanha_id = $1 and status = 'enviado'",
        campanha_id,
    )
    return {str(r["contato_id"]) for r in rows}


async def get_openai_key(usuario_id: str) -> str | None:
    """Retorna a chave OpenAI configurada pelo usuário no painel (ou None para usar o .env)."""
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        "select openai_api_key from public.integracoes where usuario_id = $1",
        usuario_id,
    )
    return row["openai_api_key"] if row and row["openai_api_key"] else None


async def get_assistente(usuario_id: str) -> dict | None:
    """Configuração do assistente de IA (atendimento automático) do usuário.

    LEGADO: retorna o primeiro assistente do usuário. Usado só como fallback
    quando a instância que recebeu a mensagem ainda não tem assistente próprio
    (get_assistente_by_instancia). No modelo atual o roteamento é por instância.
    """
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select usuario_id, ativo, empresa_nome, empresa_info,
               horario_funcionamento, instrucao, atendente_telefone,
               notificar_rotativo, pausa_ativa, pausa_minutos,
               coalesce(ler_imagem, false) as ler_imagem, instrucao_imagem,
               coalesce(ler_documento, false) as ler_documento, instrucao_documento
        from public.assistentes
        where usuario_id = $1
        order by instancia_id nulls last, created_at
        limit 1
        """,
        usuario_id,
    )
    return dict(row) if row else None


async def get_assistente_by_instancia(instancia_id: str) -> dict | None:
    """Assistente vinculado a UMA instância (canal). É o roteamento atual:
    cada número/instância tem seu próprio assistente (1 instância -> 1 assistente).
    Retorna None se a instância ainda não tem assistente vinculado (aí o webhook
    cai no fallback por usuário)."""
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select usuario_id, ativo, empresa_nome, empresa_info,
               horario_funcionamento, instrucao, atendente_telefone,
               notificar_rotativo, pausa_ativa, pausa_minutos,
               coalesce(ler_imagem, false) as ler_imagem, instrucao_imagem,
               coalesce(ler_documento, false) as ler_documento, instrucao_documento
        from public.assistentes
        where instancia_id = $1
        """,
        instancia_id,
    )
    return dict(row) if row else None


async def get_canais_para_disparo(usuario_id: str) -> list[dict]:
    """Candidatos a canal de DISPARO: toda instância do usuário com token, que NÃO
    seja de uso exclusivo de notificação.

    NÃO filtra pelo `status` gravado no banco de propósito — ele fica defasado
    quando a instância é excluída/reconectada direto no painel da UAzAPI. Quem
    decide se o canal entra no roteamento é a validação AO VIVO feita no
    orquestrador (uazapi.consultar_status). Assim, canal recém-conectado entra e
    canal-fantasma (excluído na UAzAPI) sai — sem depender de alguém abrir a tela
    de Canais para sincronizar.

    Retorna também o `status` gravado, para o orquestrador só reescrever o banco
    quando o estado ao vivo divergir, e o `bloqueado_ate` (cooldown por restrição
    temporária do WhatsApp) — quem decide pular o canal é o orquestrador, que
    registra no log da campanha QUAL número ficou de fora e até quando.
    """
    pool = get_supabase_pool()
    rows = await pool.fetch(
        """
        select id, uazapi_token, phone, uazapi_instance_name, status,
               bloqueado_ate, bloqueio_motivo
        from public.instancias
        where usuario_id = $1
          and uazapi_token is not null and uazapi_token <> ''
          and coalesce(uso_notificacao, false) = false
        order by created_at asc
        """,
        usuario_id,
    )
    return [dict(r) for r in rows]


async def marcar_status_instancia(instancia_id: str, status: str) -> None:
    """Reescreve o status de uma instância no banco (cura defasagem detectada ao
    vivo). Best-effort: usado pelo orquestrador quando a UAzAPI diverge do banco."""
    pool = get_supabase_pool()
    await pool.execute(
        "update public.instancias set status = $2 where id = $1",
        instancia_id, status,
    )


async def bloquear_instancia_ate(instancia_id: str, ate, motivo: str) -> None:
    """Coloca o canal em cooldown: fora do roteamento até `ate`.

    Usado quando o WhatsApp devolve restrição temporária (erro 463) — a sessão
    está ok, mas a conta não pode INICIAR novas conversas. Insistir só piora a
    reputação do número, então gravamos o bloqueio para que as próximas campanhas
    já nasçam sabendo (o estado em memória do disparo morre com ele)."""
    pool = get_supabase_pool()
    await pool.execute(
        "update public.instancias set bloqueado_ate = $2, bloqueio_motivo = $3 where id = $1",
        instancia_id, ate, (motivo or "")[:500],
    )


async def liberar_instancia(instancia_id: str) -> None:
    """Limpa o cooldown do canal (voltou a enviar com sucesso)."""
    pool = get_supabase_pool()
    await pool.execute(
        "update public.instancias set bloqueado_ate = null, bloqueio_motivo = null where id = $1",
        instancia_id,
    )


async def get_canal_notificacao(usuario_id: str) -> dict | None:
    """Canal conectado marcado como 'uso para notificação de atendentes' (se houver)."""
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select id, uazapi_token, phone, uazapi_instance_name
        from public.instancias
        where usuario_id = $1 and status = 'connected'
          and coalesce(uso_notificacao, false) = true
        order by created_at asc
        limit 1
        """,
        usuario_id,
    )
    return dict(row) if row else None


async def inserir_log_campanha(
    *,
    campanha_id: str,
    usuario_id: str,
    nivel: str,
    evento: str,
    detalhe: str | None = None,
    canal_id: str | None = None,
) -> None:
    pool = get_supabase_pool()
    await pool.execute(
        """
        insert into public.campanha_logs
            (campanha_id, usuario_id, nivel, evento, detalhe, canal_id)
        values ($1, $2, $3, $4, $5, $6)
        """,
        campanha_id, usuario_id, nivel, evento, detalhe, canal_id,
    )


async def get_logs_campanha(campanha_id: str) -> list[dict]:
    pool = get_supabase_pool()
    rows = await pool.fetch(
        """
        select id, nivel, evento, detalhe, canal_id, created_at
        from public.campanha_logs
        where campanha_id = $1
        order by created_at asc
        """,
        campanha_id,
    )
    return [
        {**dict(r), "created_at": r["created_at"].isoformat(), "id": str(r["id"])}
        for r in rows
    ]


# ── Follow-up ────────────────────────────────────────────────────────────────

async def get_followup_config_aplicavel(campanha_id: str, usuario_id: str) -> dict | None:
    """Config de follow-up aplicável à campanha: a específica (se houver) tem
    prioridade; senão a global (campanha_id IS NULL) do mesmo usuário."""
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select id, campanha_id, usuario_id, ativo
        from public.followup_configs
        where ativo = true and usuario_id = $2
          and (campanha_id = $1 or campanha_id is null)
        order by (campanha_id is null) asc   -- específica (false) antes da global (true)
        limit 1
        """,
        campanha_id, usuario_id,
    )
    return dict(row) if row else None


async def get_canal_por_contato(campanha_id: str, contato_ids: list[str]) -> dict[str, str]:
    """Mapa contato_id -> canal_id do disparo enviado (para follow-up sair pelo mesmo número)."""
    if not contato_ids:
        return {}
    pool = get_supabase_pool()
    rows = await pool.fetch(
        """
        select distinct on (contato_id) contato_id, canal_id
        from public.disparos
        where campanha_id = $1 and status = 'enviado' and canal_id is not null
          and contato_id = any($2::uuid[])
        order by contato_id, created_at desc
        """,
        campanha_id, contato_ids,
    )
    return {str(r["contato_id"]): str(r["canal_id"]) for r in rows if r["canal_id"]}


async def get_followup_etapas(config_id: str) -> list[dict]:
    pool = get_supabase_pool()
    rows = await pool.fetch(
        "select id, config_id, ordem, delay_minutos, modo_mensagem, mensagem from public.followup_etapas where config_id = $1 order by ordem asc",
        config_id,
    )
    return [dict(r) for r in rows]


async def bulk_inserir_followup_disparos(
    *,
    config_id: str,
    etapa_id: str,
    campanha_id: str,
    contato_ids: list[str],
    usuario_id: str,
    canal_id: str,
    agendado_para,
) -> None:
    if not contato_ids:
        return
    pool = get_supabase_pool()
    await pool.executemany(
        """
        insert into public.followup_disparos
            (config_id, etapa_id, campanha_id, contato_id, usuario_id, canal_id, agendado_para)
        values ($1, $2, $3, $4, $5, $6, $7)
        on conflict do nothing
        """,
        [(config_id, etapa_id, campanha_id, cid, usuario_id, canal_id, agendado_para) for cid in contato_ids],
    )


async def bulk_inserir_followup_disparos_por_canal(
    *,
    config_id: str,
    etapa_id: str,
    campanha_id: str,
    usuario_id: str,
    rows: list[tuple[str, str]],   # (contato_id, canal_id)
    agendado_para,
) -> None:
    """Insere disparos de follow-up com o canal específico de cada contato."""
    if not rows:
        return
    pool = get_supabase_pool()
    await pool.executemany(
        """
        insert into public.followup_disparos
            (config_id, etapa_id, campanha_id, contato_id, usuario_id, canal_id, agendado_para)
        values ($1, $2, $3, $4, $5, $6, $7)
        on conflict do nothing
        """,
        [(config_id, etapa_id, campanha_id, cid, usuario_id, canal_id, agendado_para) for cid, canal_id in rows],
    )


async def inserir_followup_disparo(
    *,
    config_id: str,
    etapa_id: str,
    campanha_id: str,
    contato_id: str,
    usuario_id: str,
    canal_id: str,
    agendado_para,
) -> None:
    pool = get_supabase_pool()
    await pool.execute(
        """
        insert into public.followup_disparos
            (config_id, etapa_id, campanha_id, contato_id, usuario_id, canal_id, agendado_para)
        values ($1, $2, $3, $4, $5, $6, $7)
        """,
        config_id, etapa_id, campanha_id, contato_id, usuario_id, canal_id, agendado_para,
    )


async def agendar_followup_etapa1_idempotente(
    *,
    config_id: str,
    etapa_id: str,
    campanha_id: str,
    contato_id: str,
    usuario_id: str,
    canal_id: str,
    agendado_para,
) -> bool:
    """Inscreve um contato na etapa 1 do follow-up SOMENTE se ele ainda não estiver
    na sequência (campanha+contato+config). Retorna True se inseriu, False se já
    existia. Evita inscrição/duplicação ao agendar por contato (no envio) e no
    backfill (na retomada)."""
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        insert into public.followup_disparos
            (config_id, etapa_id, campanha_id, contato_id, usuario_id, canal_id, agendado_para)
        select $1, $2, $3, $4, $5, $6, $7
        where not exists (
            select 1 from public.followup_disparos
            where campanha_id = $3 and contato_id = $4 and config_id = $1
        )
        -- Lead sem interesse nunca volta a ser inscrito (nem em campanhas futuras).
        and not exists (
            select 1 from public.contatos
            where id = $4 and followup_excluido = true
        )
        returning id
        """,
        config_id, etapa_id, campanha_id, contato_id, usuario_id, canal_id, agendado_para,
    )
    return row is not None


async def get_disparos_enviados_para_followup(campanha_id: str) -> list[dict]:
    """Contatos que JÁ receberam o disparo (status=enviado), com o canal usado e o
    momento do envio — base para agendar o follow-up contando do recebimento."""
    pool = get_supabase_pool()
    rows = await pool.fetch(
        """
        select distinct on (contato_id) contato_id, canal_id, enviado_em
        from public.disparos
        where campanha_id = $1 and status = 'enviado'
        order by contato_id, created_at desc
        """,
        campanha_id,
    )
    return [
        {
            "contato_id": str(r["contato_id"]),
            "canal_id": str(r["canal_id"]) if r["canal_id"] else None,
            "enviado_em": r["enviado_em"],
        }
        for r in rows
    ]


async def atualizar_followup_disparo(
    disparo_id: str,
    *,
    status: str,
    mensagem_enviada: str | None = None,
) -> None:
    pool = get_supabase_pool()
    enviado_em = _now() if status == "enviado" else None
    await pool.execute(
        """
        update public.followup_disparos
        set status = $2, mensagem_enviada = coalesce($3, mensagem_enviada), enviado_em = coalesce($4, enviado_em)
        where id = $1
        """,
        disparo_id, status, mensagem_enviada, enviado_em,
    )


async def cancelar_followups_contato(*, campanha_id: str, contato_id: str) -> None:
    pool = get_supabase_pool()
    await pool.execute(
        "update public.followup_disparos set status = 'respondeu' where campanha_id = $1 and contato_id = $2 and status = 'pendente'",
        campanha_id, contato_id,
    )


async def get_contexto_disparo_por_telefone(
    *, usuario_id: str, telefones: list[str], dias: int = 60
) -> dict | None:
    """Último disparo ENVIADO para qualquer uma das formas do telefone.

    Fallback do contexto que o disparo grava no Redis (`conv:{tid}`): se a chave
    expirou, foi perdida num flush ou ficou sob outra variante do número, ainda
    assim conseguimos ligar a resposta do cliente à campanha que a originou —
    sem isso a resposta não entrava em `disparos.respondido_em` e a campanha
    aparecia com 0 respostas no painel.
    """
    if not telefones:
        return None
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        r"""
        with alvo as (
            select id from public.contatos
            where usuario_id = $1
              and regexp_replace(telefone, '\D', '', 'g') = any($2::text[])
        )
        select d.campanha_id, d.contato_id
        from public.disparos d
        join alvo on alvo.id = d.contato_id
        where d.usuario_id = $1
          and d.status = 'enviado'
          and d.created_at > now() - make_interval(days => $3::int)
        order by d.created_at desc
        limit 1
        """,
        usuario_id, telefones, dias,
    )
    if not row:
        return None
    return {"campanha_id": str(row["campanha_id"]), "contato_id": str(row["contato_id"])}


async def contato_ja_respondeu(campanha_id: str, contato_id: str) -> bool:
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        "select id from public.disparos where campanha_id = $1 and contato_id = $2 and respondido_em is not null limit 1",
        campanha_id, contato_id,
    )
    return row is not None


async def marcar_contato_sem_interesse(*, contato_id: str, motivo: str | None = None) -> None:
    """Marca o contato como SEM interesse (negativa) → excluído de TODAS as
    sequências de follow-up, atuais e futuras, em qualquer campanha. Idempotente:
    só preenche o instante/motivo na primeira vez."""
    pool = get_supabase_pool()
    await pool.execute(
        "update public.contatos set followup_excluido = true, "
        "followup_excluido_em = coalesce(followup_excluido_em, now()), "
        "followup_excluido_motivo = coalesce(followup_excluido_motivo, $2) "
        "where id = $1",
        contato_id, motivo,
    )


async def cancelar_todos_followups_contato(*, contato_id: str) -> None:
    """Cancela os follow-ups pendentes do contato em TODAS as campanhas (não só na
    atual). Usado quando o lead demonstra não ter interesse."""
    pool = get_supabase_pool()
    await pool.execute(
        "update public.followup_disparos set status = 'cancelado' "
        "where contato_id = $1 and status = 'pendente'",
        contato_id,
    )


async def contato_followup_excluido(contato_id: str) -> bool:
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        "select 1 from public.contatos where id = $1 and followup_excluido = true",
        contato_id,
    )
    return row is not None


async def get_followup_pendentes() -> list[dict]:
    """Busca follow-ups pendentes vencidos com todas as informações necessárias para envio."""
    pool = get_supabase_pool()
    rows = await pool.fetch(
        """
        select
            fd.id, fd.config_id, fd.etapa_id, fd.campanha_id,
            fd.contato_id, fd.usuario_id, fd.canal_id,
            fe.ordem          as etapa_ordem,
            fe.delay_minutos  as etapa_delay,
            fe.modo_mensagem  as etapa_modo,
            fe.mensagem       as etapa_mensagem,
            ne.id             as next_etapa_id,
            ne.delay_minutos  as next_etapa_delay,
            c.nome            as contato_nome,
            c.telefone        as contato_telefone,
            c.observacao      as contato_obs,
            c.followup_excluido as contato_excluido,
            i.uazapi_token    as canal_token
        from public.followup_disparos fd
        join public.followup_etapas fe  on fe.id = fd.etapa_id
        join public.followup_configs fc on fc.id = fd.config_id
        left join public.followup_etapas ne on ne.config_id = fd.config_id and ne.ordem = fe.ordem + 1
        join public.contatos  c on c.id  = fd.contato_id
        join public.instancias i on i.id = fd.canal_id
        where fd.status = 'pendente'
          and fd.agendado_para <= now()
          and fc.ativo = true
        order by fd.agendado_para asc
        limit 100
        """
    )
    return [
        {
            **dict(r),
            "id": str(r["id"]),
            "config_id": str(r["config_id"]),
            "etapa_id": str(r["etapa_id"]),
            "campanha_id": str(r["campanha_id"]),
            "contato_id": str(r["contato_id"]),
            "usuario_id": str(r["usuario_id"]),
            "canal_id": str(r["canal_id"]) if r["canal_id"] else None,
            "next_etapa_id": str(r["next_etapa_id"]) if r["next_etapa_id"] else None,
        }
        for r in rows
    ]


async def get_metricas_followup(config_id: str) -> dict:
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select
            count(*) filter (where true)                     as total,
            count(*) filter (where status = 'enviado')       as enviados,
            count(*) filter (where status = 'respondeu')     as responderam,
            count(*) filter (where status = 'pendente')      as pendentes,
            count(*) filter (where status = 'cancelado')     as cancelados
        from public.followup_disparos
        where config_id = $1
        """,
        config_id,
    )
    return dict(row) if row else {"total": 0, "enviados": 0, "responderam": 0, "pendentes": 0, "cancelados": 0}


async def get_campanhas_agendadas_vencidas() -> list[dict]:
    """Campanhas em rascunho cujo horário agendado já chegou."""
    pool = get_supabase_pool()
    rows = await pool.fetch(
        """
        select id from public.campanhas
        where status = 'rascunho'
          and agendado_para is not null
          and agendado_para <= now()
        """
    )
    return [dict(r) for r in rows]


async def registrar_resposta_contato(
    *,
    campanha_id: str,
    contato_id: str,
    resposta_texto: str,
) -> bool:
    """Marca o disparo (mais recente) desse contato/campanha como respondido.

    Atualiza sempre o texto para a última mensagem, mas só define respondido_em
    na PRIMEIRA resposta. Retorna True se foi a primeira resposta deste contato
    (para o chamador incrementar o contador de respostas uma única vez).
    """
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        with alvo as (
            select id, respondido_em from public.disparos
            where campanha_id = $1 and contato_id = $2
            order by created_at desc
            limit 1
        )
        update public.disparos d
        set resposta_texto = $3,
            respondido_em = coalesce(d.respondido_em, $4)
        from alvo
        where d.id = alvo.id
        returning (alvo.respondido_em is null) as primeira
        """,
        campanha_id, contato_id, resposta_texto, _now(),
    )
    return bool(row and row["primeira"])
