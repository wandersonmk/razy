// POST /api/conversas/:id/fechar
// Fecha/resolve o atendimento (registra closed_at/resolved_at — a diferença
// closed_at-opened_at é o "tempo de atendimento" usado no relatório) e libera
// a conversa (assigned_to_professional_id volta a null).
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const atuais = await supabaseFetch(
    event,
    `/conversas?id=eq.${id}&select=id,assigned_to_professional_id,profissional:profissionais!conversas_assigned_to_professional_id_fkey(nome)`
  ) as any[]
  const atual = atuais?.[0]
  if (!atual) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })

  const agora = new Date().toISOString()
  const [atualizado] = await supabaseFetch(event, `/conversas?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({
      closed_at: agora,
      resolved_at: agora,
      status: 'fechada',
      assigned_to_professional_id: null,
      assigned_at: null,
      assigned_by: null
    })
  }) as any[]

  try {
    await supabaseFetch(event, '/conversa_atendentes_historico', {
      method: 'POST',
      headers: { Prefer: 'return=minimal' },
      body: JSON.stringify({
        usuario_id: user.id,
        conversa_id: id,
        profissional_id: atual.assigned_to_professional_id,
        profissional_nome_snapshot: atual.profissional?.nome || null,
        acao: 'fechado',
        created_by: user.id
      })
    })
  } catch (e) {
    console.error('[conversas/fechar] falha ao gravar histórico:', e)
  }

  return atualizado
})
