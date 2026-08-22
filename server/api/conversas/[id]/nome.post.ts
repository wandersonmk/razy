// POST /api/conversas/:id/nome
// Renomeia o contato manualmente. Marca nome_editado=true — o trigger do
// webhook (mensagens_before_insert) para de sobrescrever esse nome com o
// pushName que chega do WhatsApp assim que essa flag está ligada.
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const body = await readBody<{ nome_contato?: string }>(event)
  const nome = body?.nome_contato?.trim()
  if (!nome) throw createError({ statusCode: 400, statusMessage: 'nome_contato é obrigatório' })

  const atualizado = await supabaseFetch(event, `/conversas?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ nome_contato: nome, nome_editado: true })
  }) as any[]
  if (!atualizado?.length) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })
  return atualizado[0]
})
