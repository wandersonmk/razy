// GET /api/profissionais/:id/assistente
// Config da IA independente desse profissional (tabela assistentes_profissionais).
// Retorna null se ainda não foi criada (profissional sem instância, por exemplo).
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })
  }

  const registros = await supabaseFetch(
    event,
    `/assistentes_profissionais?profissional_id=eq.${id}&select=*`
  ) as any[]

  return registros?.[0] || null
})
