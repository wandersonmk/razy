// GET /api/conversas/:id/historico — últimos eventos de atribuição/fechamento
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  return await supabaseFetch(
    event,
    `/conversa_atendentes_historico?conversa_id=eq.${id}&select=*&order=created_at.desc&limit=20`
  )
})
