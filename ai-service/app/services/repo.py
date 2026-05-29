"""Acesso aos dados de negócio no Supabase (contatos, campanhas, disparos, instâncias).

O serviço conecta como o papel `postgres` (bypassa RLS), pois é um worker
de backend confiável. As queries são parametrizadas.
"""

from datetime import datetime, timezone

from app.db.supabase import get_supabase_pool


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Leitura ──────────────────────────────────────────────────────────────────

async def get_campanha(campanha_id: str) -> dict | None:
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select id, usuario_id, publico_id, canal_id, nome, mensagem,
               modo_mensagem, intervalo_segundos, status,
               total_enviados, total_falhas, total_respostas
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
    """Busca a instância pelo uazapi_token — usado para resolver o webhook."""
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        select id, usuario_id, uazapi_instance_name, uazapi_token, phone, status
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
) -> str:
    """Registra um disparo e retorna o id criado."""
    pool = get_supabase_pool()
    enviado_em = _now() if status == "enviado" else None
    row = await pool.fetchrow(
        """
        insert into public.disparos
            (campanha_id, contato_id, usuario_id, status, mensagem_enviada, erro, enviado_em)
        values ($1, $2, $3, $4, $5, $6, $7)
        returning id
        """,
        campanha_id, contato_id, usuario_id, status, mensagem_enviada, erro, enviado_em,
    )
    return str(row["id"])


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


async def claim_campanha(campanha_id: str) -> bool:
    """Marca a campanha como em_andamento de forma atômica.

    Retorna True se ESTE processo conseguiu o claim — evita disparo duplicado
    (clique duplo, ou múltiplos workers do scheduler).
    """
    pool = get_supabase_pool()
    row = await pool.fetchrow(
        """
        update public.campanhas
        set status = 'em_andamento', iniciado_em = $2
        where id = $1 and status in ('rascunho', 'pausada')
        returning id
        """,
        campanha_id, _now(),
    )
    return row is not None


async def get_campanha_status(campanha_id: str) -> str | None:
    """Leitura leve do status (usada para detectar pausa durante o disparo)."""
    pool = get_supabase_pool()
    row = await pool.fetchrow("select status from public.campanhas where id = $1", campanha_id)
    return row["status"] if row else None


async def get_contatos_ja_enviados(campanha_id: str) -> set[str]:
    """IDs de contatos que já receberam (status enviado) — para retomar sem reenviar."""
    pool = get_supabase_pool()
    rows = await pool.fetch(
        "select contato_id from public.disparos where campanha_id = $1 and status = 'enviado'",
        campanha_id,
    )
    return {str(r["contato_id"]) for r in rows}


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
) -> None:
    """Marca o disparo desse contato/campanha como respondido (mais recente)."""
    pool = get_supabase_pool()
    await pool.execute(
        """
        update public.disparos
        set resposta_texto = $3, respondido_em = $4
        where id = (
            select id from public.disparos
            where campanha_id = $1 and contato_id = $2
            order by created_at desc
            limit 1
        )
        """,
        campanha_id, contato_id, resposta_texto, _now(),
    )
