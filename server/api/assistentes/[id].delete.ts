// DELETE /api/assistentes/:id
// Remove um assistente (hard delete). A propriedade é garantida pelo RLS
// (usuario_id = auth.uid()). Excluir um assistente NÃO afeta a instância;
// a instância só fica sem assistente até ser reatribuída a outro.
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })
  }

  await supabaseFetch(event, `/assistentes?id=eq.${id}`, {
    method: 'DELETE',
    headers: { Prefer: 'return=minimal' }
  })

  return { ok: true }
})
