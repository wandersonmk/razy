// POST /api/clientes/despausar — remove a pausa de atendimento de um contato
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const config = useRuntimeConfig()
  const body = await readBody<{ telefone?: string }>(event)
  if (!body?.telefone) {
    throw createError({ statusCode: 400, statusMessage: 'telefone obrigatório' })
  }
  if (!config.aiServiceUrl || !config.internalToken) {
    throw createError({ statusCode: 503, statusMessage: 'ai-service não configurado' })
  }
  const baseUrl = String(config.aiServiceUrl).replace(/\/$/, '')
  const res = await fetch(`${baseUrl}/assistente/pausas/remover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Internal-Token': config.internalToken as string },
    body: JSON.stringify({ usuario_id: user.id, telefone: body.telefone })
  })
  const data = await res.json().catch(() => ({ removidos: 0 }))
  if (!res.ok) throw createError({ statusCode: res.status, statusMessage: 'Erro ao despausar' })
  return data
})
