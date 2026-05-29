// DELETE /api/followups/[id]
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const configs = await supabaseFetch(event, `/followup_configs?id=eq.${id}&select=id,usuario_id`)
  if (!configs?.[0] || configs[0].usuario_id !== user.id) {
    throw createError({ statusCode: 404, statusMessage: 'Config não encontrada' })
  }

  await supabaseFetch(event, `/followup_configs?id=eq.${id}`, { method: 'DELETE' })
  return { deleted: true }
})
