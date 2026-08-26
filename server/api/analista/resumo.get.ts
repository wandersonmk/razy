// GET /api/analista/resumo — números da operação mostrados ao abrir o painel.
// Falha em silêncio (retorna null) de propósito: é informação de apoio; se o
// ai-service estiver fora, o painel ainda tem de abrir e aceitar perguntas.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const config = useRuntimeConfig()

  if (!config.aiServiceUrl || !config.internalToken) return null

  const baseUrl = String(config.aiServiceUrl).replace(/\/$/, '')
  try {
    const res = await fetch(`${baseUrl}/analista/resumo?usuario_id=${user.id}`, {
      headers: { 'X-Internal-Token': config.internalToken as string }
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
})
