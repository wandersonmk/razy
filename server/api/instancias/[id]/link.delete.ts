// DELETE /api/instancias/:id/link
// Revoga o link compartilhável (o token existente para de funcionar
// imediatamente — as RPCs públicas comparam share_token = p_token, e null
// nunca bate com nada).
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  await supabaseFetch(event, `/instancias?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ share_token: null })
  })

  return { ok: true }
})
