// PATCH /api/instancias/:id — atualiza campos da instância (nome e/ou uso_notificacao).
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const body = await readBody<{ nome_instancia?: string; uso_notificacao?: boolean }>(event)

  const updates: Record<string, any> = {}
  if (typeof body?.nome_instancia === 'string') {
    const nome = body.nome_instancia.trim()
    if (!nome) throw createError({ statusCode: 400, statusMessage: 'nome_instancia não pode ser vazio' })
    updates.nome_instancia = nome
  }
  if (typeof body?.uso_notificacao === 'boolean') {
    updates.uso_notificacao = body.uso_notificacao
  }

  if (Object.keys(updates).length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'nada para atualizar' })
  }

  const [atualizada] = await supabaseFetch(event, `/instancias?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates)
  })

  if (!atualizada) {
    throw createError({ statusCode: 404, statusMessage: 'Instância não encontrada' })
  }

  return atualizada
})
