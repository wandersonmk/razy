// PATCH /api/profissionais/:id/assistente
// Liga/desliga e configura a IA independente do profissional. Faz upsert: se a
// linha ainda não existe (profissional sem instância na hora da criação), cria
// antes de aplicar o patch — a página nunca precisa se preocupar com isso.
const CAMPOS_PERMITIDOS = [
  'ativo',
  'empresa_nome', 'empresa_info', 'horario_funcionamento', 'instrucao',
  'ler_imagem', 'instrucao_imagem', 'ler_documento', 'instrucao_documento',
  'pausa_ativa', 'pausa_minutos'
] as const

export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })
  }

  const prof = await supabaseFetch(
    event,
    `/profissionais?id=eq.${id}&usuario_id=eq.${user.id}&select=id`
  ) as any[]
  if (!prof?.length) {
    throw createError({ statusCode: 403, statusMessage: 'Profissional não pertence ao usuário' })
  }

  const body = await readBody<Record<string, unknown>>(event)
  const payload: Record<string, unknown> = {}
  for (const campo of CAMPOS_PERMITIDOS) {
    if (campo in body) payload[campo] = body[campo]
  }
  if (Object.keys(payload).length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'Nada para atualizar' })
  }

  const existentes = await supabaseFetch(
    event,
    `/assistentes_profissionais?profissional_id=eq.${id}&select=id`
  ) as any[]

  if (!existentes?.length) {
    const [criado] = await supabaseFetch(event, '/assistentes_profissionais', {
      method: 'POST',
      body: JSON.stringify({ usuario_id: user.id, profissional_id: id, ativo: false, ...payload })
    })
    return criado
  }

  payload.updated_at = new Date().toISOString()
  const [atualizado] = await supabaseFetch(event, `/assistentes_profissionais?profissional_id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })

  return atualizado
})
