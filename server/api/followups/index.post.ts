// POST /api/followups — cria config + etapas
// campanha_id null/ausente => sequência GLOBAL (aplica a todas as campanhas).
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

  // Remove config anterior do mesmo escopo (específica da campanha OU global)
  const filtroEscopo = isGlobal ? 'campanha_id=is.null' : `campanha_id=eq.${campanhaId}`
  await supabaseFetch(event, `/followup_configs?${filtroEscopo}&usuario_id=eq.${user.id}`, {
    method: 'DELETE'
  })

  // Cria nova config
  const configs = await supabaseFetch(event, '/followup_configs', {
    method: 'POST',
    body: JSON.stringify({ campanha_id: campanhaId, usuario_id: user.id, ativo: true })
  })
  const config = Array.isArray(configs) ? configs[0] : configs

  // Cria etapas
  const etapasPayload = body.etapas.map((e: any, i: number) => ({
    config_id: config.id,
    ordem: i + 1,
    delay_minutos: Number(e.delay_minutos) || 60,
    modo_mensagem: e.modo_mensagem || 'ia',
    mensagem: e.mensagem || null
  }))
  const etapas = await supabaseFetch(event, '/followup_etapas', {
    method: 'POST',
    body: JSON.stringify(etapasPayload)
  })

  return { ...config, etapas: etapas || [] }
})
