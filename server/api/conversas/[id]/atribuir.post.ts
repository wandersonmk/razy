// POST /api/conversas/:id/atribuir
// Body: { profissional_id: string | null } — null remove a atribuição.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const body = await readBody<{ profissional_id?: string | null }>(event)
  const profissionalId = body?.profissional_id || null

  let nomeSnapshot: string | null = null
  if (profissionalId) {
    const prof = await supabaseFetch(
      event,
      `/profissionais?id=eq.${profissionalId}&usuario_id=eq.${user.id}&select=id,nome`
    ) as any[]
    if (!prof?.length) throw createError({ statusCode: 403, statusMessage: 'Profissional não pertence ao usuário' })
    nomeSnapshot = prof[0].nome
  }

  const payload: Record<string, unknown> = profissionalId
    ? { assigned_to_professional_id: profissionalId, assigned_at: new Date().toISOString(), assigned_by: user.id }
    : { assigned_to_professional_id: null, assigned_at: null, assigned_by: null }

  const atualizado = await supabaseFetch(event, `/conversas?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  }) as any[]
  if (!atualizado?.length) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })

  try {
    await supabaseFetch(event, '/conversa_atendentes_historico', {
      method: 'POST',
      headers: { Prefer: 'return=minimal' },
      body: JSON.stringify({
        usuario_id: user.id,
        conversa_id: id,
        profissional_id: profissionalId,
        profissional_nome_snapshot: nomeSnapshot,
        acao: profissionalId ? 'atribuido' : 'desatribuido',
        created_by: user.id
      })
    })
  } catch (e) {
    console.error('[conversas/atribuir] falha ao gravar histórico:', e)
  }

  return atualizado[0]
})
