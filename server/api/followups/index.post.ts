// POST /api/followups — cria OU atualiza (in-place) a sequência do escopo + etapas.
// campanha_id null/ausente => sequência GLOBAL (aplica a todas as campanhas).
//
// IMPORTANTE — por que NÃO deletamos a config ao editar:
//   followup_disparos.config_id é ON DELETE CASCADE. Apagar a config apagaria
//   TODO o histórico de follow-ups (followup_disparos) e ainda cancelaria os
//   envios PENDENTES (em voo) da campanha. Por isso, ao editar reaproveitamos a
//   config existente (preservando id e o estado `ativo` — ex.: sequência pausada)
//   e reconciliamos as etapas pela `ordem`, mantendo os ids das etapas que já
//   existem (o scheduler casa a etapa atual de um disparo pelo etapa_id), o que
//   preserva o histórico e os agendamentos em andamento.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const body = await readBody(event)

  if (!Array.isArray(body?.etapas) || body.etapas.length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'etapas são obrigatórias' })
  }

  const isGlobal = !body.campanha_id || body.campanha_id === '__all__'
  const campanhaId: string | null = isGlobal ? null : body.campanha_id

  // Se específica, verifica propriedade da campanha
  if (!isGlobal) {
    const campanhas = await supabaseFetch(
      event,
      `/campanhas?id=eq.${campanhaId}&select=id,usuario_id`
    )
    if (!campanhas?.[0] || campanhas[0].usuario_id !== user.id) {
      throw createError({ statusCode: 404, statusMessage: 'Campanha não encontrada' })
    }
  }

  const novasEtapas = body.etapas.map((e: any, i: number) => ({
    ordem: i + 1,
    delay_minutos: Number(e.delay_minutos) || 60,
    modo_mensagem: e.modo_mensagem || 'ia',
    mensagem: e.mensagem || null,
  }))

  // Procura a config existente no mesmo escopo (global OU da campanha).
  const filtroEscopo = isGlobal ? 'campanha_id=is.null' : `campanha_id=eq.${campanhaId}`
  const existentes = await supabaseFetch(
    event,
    `/followup_configs?${filtroEscopo}&usuario_id=eq.${user.id}&select=id,ativo,campanha_id,criado_em&order=criado_em.asc`
  )
  const existente = Array.isArray(existentes) ? existentes[0] : null

  let config: any
  let etapasAtuais: any[] = []
  if (!existente) {
    // ── Criação: ainda não há sequência neste escopo ────────────────────────
    const configs = await supabaseFetch(event, '/followup_configs', {
      method: 'POST',
      body: JSON.stringify({ campanha_id: campanhaId, usuario_id: user.id, ativo: true })
    })
    config = Array.isArray(configs) ? configs[0] : configs
  } else {
    // ── Edição in-place: preserva a config (id + ativo) e o histórico ───────
    config = existente
    etapasAtuais = await supabaseFetch(
      event,
      `/followup_etapas?config_id=eq.${config.id}&select=id,ordem&order=ordem.asc`
    ) || []
  }

  const porOrdem = new Map<number, any>(etapasAtuais.map((e: any) => [e.ordem, e]))

  // Reconciliação das etapas pela `ordem` — reaproveita os ids existentes.
  const etapasOut: any[] = []
  for (const nova of novasEtapas) {
    const atual = porOrdem.get(nova.ordem)
    if (atual) {
      // Atualiza no lugar: mantém o id → disparos pendentes/histórico seguem válidos.
      const upd = await supabaseFetch(event, `/followup_etapas?id=eq.${atual.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          delay_minutos: nova.delay_minutos,
          modo_mensagem: nova.modo_mensagem,
          mensagem: nova.mensagem,
        })
      })
      etapasOut.push(Array.isArray(upd) ? upd[0] : upd)
    } else {
      const ins = await supabaseFetch(event, '/followup_etapas', {
        method: 'POST',
        body: JSON.stringify({ config_id: config.id, ...nova })
      })
      etapasOut.push(Array.isArray(ins) ? ins[0] : ins)
    }
  }

  // Etapas removidas (ordem além do novo total): só apagamos as que NÃO têm
  // histórico/disparos — followup_disparos.etapa_id é NO ACTION e bloquearia o
  // DELETE; e, mesmo que não bloqueasse, apagar perderia o histórico daquela
  // etapa. As que já dispararam ficam preservadas (registro histórico).
  for (const etapa of etapasAtuais) {
    if (etapa.ordem <= novasEtapas.length) continue
    const refs = await supabaseFetch(
      event,
      `/followup_disparos?etapa_id=eq.${etapa.id}&select=id&limit=1`
    )
    if (!Array.isArray(refs) || refs.length === 0) {
      await supabaseFetch(event, `/followup_etapas?id=eq.${etapa.id}`, { method: 'DELETE' })
    }
  }

  return { ...config, etapas: etapasOut }
})
