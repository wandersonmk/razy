// POST /api/conversas/:id/abrir
// Assume/abre o atendimento manualmente pelo painel (a via automática é o
// profissional respondendo pelo celular — ver ai-service/app/api/webhook.py).
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const body = await readBody<{ profissional_id?: string | null }>(event).catch(() => ({} as any))

  const payload: Record<string, unknown> = {
    opened_at: new Date().toISOString(),
    closed_at: null,
    resolved_at: null,
    status: 'aberta'
  }
  if (body?.profissional_id) {
    payload.assigned_to_professional_id = body.profissional_id
    payload.assigned_at = new Date().toISOString()
    payload.assigned_by = user.id
  }

  const atualizado = await supabaseFetch(event, `/conversas?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  }) as any[]

  if (!atualizado?.length) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })
  return atualizado[0]
})
