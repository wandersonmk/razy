// POST /api/conversas/:id/despausar
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const config = useRuntimeConfig()

  const conversas = await supabaseFetch(event, `/conversas?id=eq.${id}&select=id,numero,instancia_id`)
  const conversa = conversas[0]
  if (!conversa) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })

  if (config.aiServiceUrl && config.internalToken && conversa.instancia_id) {
    const baseUrl = String(config.aiServiceUrl).replace(/\/$/, '')
    await fetch(`${baseUrl}/conversas/despausar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Internal-Token': config.internalToken as string },
      body: JSON.stringify({ usuario_id: user.id, instancia_id: conversa.instancia_id, telefone: conversa.numero })
    }).catch(() => null)
  }

  const [atualizado] = await supabaseFetch(event, `/conversas?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ tempo_pausa: null, tempo_pausa_inicio: null })
  })

  return atualizado
})
