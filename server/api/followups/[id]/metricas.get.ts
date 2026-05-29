// GET /api/followups/[id]/metricas
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const configs = await supabaseFetch(event, `/followup_configs?id=eq.${id}&select=id,usuario_id`)
  if (!configs?.[0] || configs[0].usuario_id !== user.id) {
    throw createError({ statusCode: 404, statusMessage: 'Config não encontrada' })
  }

  const disparos = await supabaseFetch(
    event,
    `/followup_disparos?config_id=eq.${id}&select=status`
  )
  const lista: any[] = disparos || []
  return {
    total:      lista.length,
    enviados:   lista.filter((d: any) => d.status === 'enviado').length,
    responderam: lista.filter((d: any) => d.status === 'respondeu').length,
    pendentes:  lista.filter((d: any) => d.status === 'pendente').length,
    cancelados: lista.filter((d: any) => d.status === 'cancelado').length,
  }
})
