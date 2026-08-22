// DELETE /api/profissionais/:id
// Remove o profissional. A instância vinculada NÃO é apagada — só fica sem dono
// (instancias.profissional_id vira null, por ON DELETE SET NULL). Se o
// profissional já tem histórico de conversa/atendimento, o banco recusa a
// exclusão (proteção contra perder rastro de atendimento).
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })
  }

  try {
    await supabaseFetch(event, `/profissionais?id=eq.${id}`, {
      method: 'DELETE',
      headers: { Prefer: 'return=minimal' }
    })
  } catch (e: any) {
    if (e?.statusCode === 409 || /foreign key/i.test(e?.statusMessage || '')) {
      throw createError({
        statusCode: 409,
        statusMessage: 'Este profissional já tem conversas/atendimentos registrados e não pode ser excluído. Desative-o em vez de excluir.'
      })
    }
    throw e
  }

  return { ok: true }
})
