// POST /api/assistentes
// Cria um assistente manualmente (extra/órfão ou já vinculado a uma instância).
// Body: { nome: string, tipo?: string, instancia_id?: string | null }
// Herda a config de um assistente existente do usuário, se houver.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const body = await readBody<{ nome?: string; tipo?: string; instancia_id?: string | null }>(event)

  const nome = body?.nome?.trim()
  if (!nome) {
    throw createError({ statusCode: 400, statusMessage: 'nome é obrigatório' })
  }

  const instanciaId = body?.instancia_id || null

  // Se veio instância, valida que é do usuário e libera de outro assistente (unique).
  if (instanciaId) {
    const inst = await supabaseFetch(
      event,
      `/instancias?id=eq.${instanciaId}&usuario_id=eq.${user.id}&select=id`
    ) as any[]
    if (!inst?.length) {
      throw createError({ statusCode: 403, statusMessage: 'Instância não pertence ao usuário' })
    }
    await supabaseFetch(event, `/assistentes?instancia_id=eq.${instanciaId}`, {
      method: 'PATCH',
      headers: { Prefer: 'return=minimal' },
      body: JSON.stringify({ instancia_id: null })
    }).catch(() => null)
  }

  const existentes = await supabaseFetch(
    event,
    `/assistentes?usuario_id=eq.${user.id}&select=empresa_nome,empresa_info,horario_funcionamento,instrucao,atendente_telefone,notificar_rotativo,pausa_ativa,pausa_minutos,ler_imagem,instrucao_imagem,ler_documento,instrucao_documento&order=created_at.asc&limit=1`
  ) as any[]
  const base = existentes?.[0] || {}

  const [assistente] = await supabaseFetch(event, '/assistentes', {
    method: 'POST',
    body: JSON.stringify({
      usuario_id: user.id,
      instancia_id: instanciaId,
      nome,
      tipo: body?.tipo?.trim() || 'principal',
      ativo: true,
      empresa_nome: base.empresa_nome ?? null,
      empresa_info: base.empresa_info ?? null,
      horario_funcionamento: base.horario_funcionamento ?? null,
      instrucao: base.instrucao ?? null,
      atendente_telefone: base.atendente_telefone ?? null,
      notificar_rotativo: base.notificar_rotativo ?? false,
      pausa_ativa: base.pausa_ativa ?? true,
      pausa_minutos: base.pausa_minutos ?? 30,
      ler_imagem: base.ler_imagem ?? false,
      instrucao_imagem: base.instrucao_imagem ?? null,
      ler_documento: base.ler_documento ?? false,
      instrucao_documento: base.instrucao_documento ?? null
    })
  })

  return assistente
})
