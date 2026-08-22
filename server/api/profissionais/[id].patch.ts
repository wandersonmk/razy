// PATCH /api/profissionais/:id
// Atualiza nome/telefone/avatar/ativo. A propriedade da linha é garantida pelo
// RLS (usuario_id = auth.uid()).
const CAMPOS_PERMITIDOS = ['nome', 'telefone', 'avatar_url', 'ativo'] as const

export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })
  }

  const body = await readBody<Record<string, unknown>>(event)

  const payload: Record<string, unknown> = {}
  for (const campo of CAMPOS_PERMITIDOS) {
    if (campo in body) payload[campo] = body[campo]
  }

  if (Object.keys(payload).length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'Nada para atualizar' })
  }

  const atualizado = await supabaseFetch(event, `/profissionais?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  }) as any[]

  if (!atualizado?.length) {
    throw createError({ statusCode: 404, statusMessage: 'Profissional não encontrado' })
  }

  return atualizado[0]
})
