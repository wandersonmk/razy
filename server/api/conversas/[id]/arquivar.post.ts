// POST /api/conversas/:id/arquivar
// Body: { arquivada: boolean }
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const body = await readBody<{ arquivada?: boolean }>(event)
  const arquivada = body?.arquivada !== false

  const atualizado = await supabaseFetch(event, `/conversas?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ arquivada })
  }) as any[]
  if (!atualizado?.length) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })
  return atualizado[0]
})
