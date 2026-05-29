// PATCH /api/followups/[id]/toggle — ativa/desativa
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  const body = await readBody(event)
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const configs = await supabaseFetch(event, `/followup_configs?id=eq.${id}&select=id,usuario_id`)
  if (!configs?.[0] || configs[0].usuario_id !== user.id) {
    throw createError({ statusCode: 404, statusMessage: 'Config não encontrada' })
  }

  const updated = await supabaseFetch(event, `/followup_configs?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ ativo: body.ativo })
  })
  return updated
})
