// POST /api/conversas/:id/excluir
// Soft delete: marca deleted_at (a listagem já filtra deleted_at=is.null).
// Não apaga `mensagens` nem mexe em `clientes` — só some da página de
// Conversas, o histórico continua no banco.
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const [conversa] = await supabaseFetch(event, `/conversas?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ deleted_at: new Date().toISOString() })
  })

  if (!conversa) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })
  return conversa
})
