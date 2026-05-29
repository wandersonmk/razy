// GET /api/campanhas/[id]/logs
// Retorna os eventos de log de uma campanha via ai-service.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const config = useRuntimeConfig()
  const id = getRouterParam(event, 'id')

  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id da campanha é obrigatório' })
  }
  if (!config.aiServiceUrl || !config.internalToken) {
    throw createError({ statusCode: 503, statusMessage: 'ai-service não configurado' })
  }

  // Verifica posse da campanha
  const campanhas = await supabaseFetch(
    event,
    `/campanhas?id=eq.${id}&select=id,usuario_id`
  )
  const campanha = campanhas[0]
  if (!campanha || campanha.usuario_id !== user.id) {
    throw createError({ statusCode: 404, statusMessage: 'Campanha não encontrada' })
  }

  const baseUrl = String(config.aiServiceUrl).replace(/\/$/, '')
  const res = await fetch(`${baseUrl}/campanhas/${id}/logs`, {
    headers: { 'X-Internal-Token': config.internalToken as string }
  })

  const data = await res.json().catch(() => ({ logs: [] }))
  if (!res.ok) {
    throw createError({ statusCode: res.status, statusMessage: 'Erro ao buscar logs' })
  }
  return data
})
