// POST /api/followups — cria config + etapas
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const body = await readBody(event)

  if (!body?.campanha_id || !Array.isArray(body?.etapas) || body.etapas.length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'campanha_id e etapas são obrigatórios' })
  }

  // Verifica propriedade da campanha
  const campanhas = await supabaseFetch(
    event,
    `/campanhas?id=eq.${body.campanha_id}&select=id,usuario_id`
  )
  if (!campanhas?.[0] || campanhas[0].usuario_id !== user.id) {
    throw createError({ statusCode: 404, statusMessage: 'Campanha não encontrada' })
  }

  // Remove config anterior se existir
  await supabaseFetch(event, `/followup_configs?campanha_id=eq.${body.campanha_id}&usuario_id=eq.${user.id}`, {
    method: 'DELETE'
  })

  // Cria nova config
  const configs = await supabaseFetch(event, '/followup_configs', {
    method: 'POST',
    body: JSON.stringify({ campanha_id: body.campanha_id, usuario_id: user.id, ativo: true })
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
