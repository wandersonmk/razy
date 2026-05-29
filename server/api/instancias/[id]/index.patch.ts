// PATCH /api/instancias/:id — atualiza campos da instância (apenas nome por enquanto).
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const body = await readBody<{ nome_instancia?: string }>(event)
  const nome = body?.nome_instancia?.trim()
  if (!nome) {
    throw createError({ statusCode: 400, statusMessage: 'nome_instancia é obrigatório' })
  }

  const [atualizada] = await supabaseFetch(event, `/instancias?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ nome_instancia: nome })
  })

  if (!atualizada) {
    throw createError({ statusCode: 404, statusMessage: 'Instância não encontrada' })
  }

  return atualizada
})
