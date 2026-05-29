// GET /api/clientes/pausas — contatos com atendimento pausado (via ai-service/Redis)
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const config = useRuntimeConfig()
  if (!config.aiServiceUrl || !config.internalToken) {
    return { pausas: [] }
  }
  const baseUrl = String(config.aiServiceUrl).replace(/\/$/, '')
  try {
    const res = await fetch(`${baseUrl}/assistente/pausas?usuario_id=${user.id}`, {
      headers: { 'X-Internal-Token': config.internalToken as string }
    })
    if (!res.ok) return { pausas: [] }
    return await res.json()
  } catch {
    return { pausas: [] }
  }
})
