// PATCH /api/assistentes/:id
// Atualiza a config do assistente e/ou REATRIBUI a instância vinculada.
// Só campos da allowlist são gravados. A propriedade da linha é garantida pelo
// RLS (usuario_id = auth.uid()); a instância destino é validada explicitamente.
const CAMPOS_PERMITIDOS = [
  'nome', 'tipo', 'ativo',
  'empresa_nome', 'empresa_info', 'horario_funcionamento', 'instrucao',
  'atendente_telefone', 'notificar_rotativo', 'pausa_ativa', 'pausa_minutos'
] as const

export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })
  }

  const body = await readBody<Record<string, unknown>>(event)

  const payload: Record<string, unknown> = {}
  for (const campo of CAMPOS_PERMITIDOS) {
    if (campo in body) payload[campo] = body[campo]
  }

  // Reatribuição de instância (pode vir null para desvincular / deixar órfão).
  if ('instancia_id' in body) {
    const novaInstancia = (body.instancia_id as string | null) || null
    if (novaInstancia) {
      const inst = await supabaseFetch(
        event,
        `/instancias?id=eq.${novaInstancia}&usuario_id=eq.${user.id}&select=id`
      ) as any[]
      if (!inst?.length) {
        throw createError({ statusCode: 403, statusMessage: 'Instância não pertence ao usuário' })
      }
      // Libera a instância de qualquer outro assistente (respeita o unique parcial).
      await supabaseFetch(event, `/assistentes?instancia_id=eq.${novaInstancia}&id=neq.${id}`, {
        method: 'PATCH',
        headers: { Prefer: 'return=minimal' },
        body: JSON.stringify({ instancia_id: null })
      }).catch(() => null)
    }
    payload.instancia_id = novaInstancia
  }

  if (Object.keys(payload).length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'Nada para atualizar' })
  }
  payload.updated_at = new Date().toISOString()

  const atualizado = await supabaseFetch(event, `/assistentes?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  }) as any[]

  if (!atualizado?.length) {
    throw createError({ statusCode: 404, statusMessage: 'Assistente não encontrado' })
  }

  return atualizado[0]
})
