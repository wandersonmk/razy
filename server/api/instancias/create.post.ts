
// POST /api/instancias/create
// Body: { nome_instancia: string }
// Cria instância na UAzAPI (POST /instance/create com admintoken) e salva no banco.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const config = useRuntimeConfig()

  if (!config.uazapiAdminToken) {
    throw createError({
      statusCode: 503,
      statusMessage: 'UAZAPI_ADMIN_TOKEN não configurado no .env'
    })
  }

  const body = await readBody<{ nome_instancia: string; profissional_id?: string | null }>(event)
  const nome = body?.nome_instancia?.trim()
  if (!nome) {
    throw createError({ statusCode: 400, statusMessage: 'nome_instancia é obrigatório' })
  }

  // Vínculo opcional com um profissional (canal por profissional). Valida que o
  // profissional é do usuário e que ainda não tem outra instância ativa — o
  // índice único do banco também garante isso, mas aqui dá um erro legível.
  const profissionalId = body?.profissional_id || null
  if (profissionalId) {
    const prof = await supabaseFetch(
      event,
      `/profissionais?id=eq.${profissionalId}&usuario_id=eq.${user.id}&select=id`
    ) as any[]
    if (!prof?.length) {
      throw createError({ statusCode: 403, statusMessage: 'Profissional não pertence ao usuário' })
    }
    const jaTemInstancia = await supabaseFetch(
      event,
      `/instancias?profissional_id=eq.${profissionalId}&status=neq.deleted&select=id`
    ) as any[]
    if (jaTemInstancia?.length) {
      throw createError({ statusCode: 409, statusMessage: 'Este profissional já tem um canal conectado' })
    }
  }

  const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')

  const uazResponse = await fetch(`${baseUrl}/instance/create`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'admintoken': config.uazapiAdminToken
    },
    body: JSON.stringify({
      name: nome,
      adminField01: user.id
    })
  })

  const uazData = await uazResponse.json().catch(() => ({}))

  if (!uazResponse.ok) {
    throw createError({
      statusCode: uazResponse.status,
      statusMessage: (uazData as any)?.response || (uazData as any)?.message || 'Erro ao criar instância na UAzAPI'
    })
  }

  const instance = (uazData as any)?.instance || {}
  const uazapi_token = instance.token || (uazData as any)?.token
  const uazapi_instance_name = instance.name || (uazData as any)?.name || nome

  if (!uazapi_token) {
    throw createError({
      statusCode: 500,
      statusMessage: 'UAzAPI não retornou token da instância'
    })
  }

  const [instancia] = await supabaseFetch(event, '/instancias', {
    method: 'POST',
    body: JSON.stringify({
      usuario_id: user.id,
      nome_instancia: nome,
      uazapi_instance_name,
      uazapi_token,
      status: 'disconnected',
      profissional_id: profissionalId
    })
  })

  // Auto-cria o assistente vinculado à nova instância (1 instância -> 1 assistente),
  // SÓ para instâncias sem profissional — é o modelo antigo (cardápio/campanha).
  // Canal por profissional usa o modelo separado (assistentes_profissionais),
  // que nasce desligado e é configurado na página "IA dos Profissionais".
  // Herda a config de um assistente já existente do usuário (se houver) para o novo
  // número já responder com a mesma instrução; senão nasce com os defaults do banco.
  // Não derruba a criação da instância se isto falhar.
  if (!profissionalId) try {
    const existentes = await supabaseFetch(
      event,
      `/assistentes?usuario_id=eq.${user.id}&select=empresa_nome,empresa_info,horario_funcionamento,instrucao,atendente_telefone,notificar_rotativo,pausa_ativa,pausa_minutos&order=created_at.asc&limit=1`
    ) as any[]
    const base = existentes?.[0] || {}
    await supabaseFetch(event, '/assistentes', {
      method: 'POST',
      headers: { Prefer: 'return=minimal' },
      body: JSON.stringify({
        usuario_id: user.id,
        instancia_id: instancia.id,
        nome,
        tipo: 'principal',
        ativo: true,
        empresa_nome: base.empresa_nome ?? null,
        empresa_info: base.empresa_info ?? null,
        horario_funcionamento: base.horario_funcionamento ?? null,
        instrucao: base.instrucao ?? null,
        atendente_telefone: base.atendente_telefone ?? null,
        notificar_rotativo: base.notificar_rotativo ?? false,
        pausa_ativa: base.pausa_ativa ?? true,
        pausa_minutos: base.pausa_minutos ?? 30
      })
    })
  } catch (e) {
    console.error('[instancias/create] falha ao auto-criar assistente:', e)
  }

  // Instância de profissional: já deixa a linha de IA própria pronta (desligada),
  // pra página "IA dos Profissionais" ter o que editar sem precisar criar nada.
  if (profissionalId) try {
    await supabaseFetch(event, '/assistentes_profissionais', {
      method: 'POST',
      headers: { Prefer: 'return=minimal' },
      body: JSON.stringify({
        usuario_id: user.id,
        profissional_id: profissionalId,
        ativo: false
      })
    })
  } catch (e) {
    console.error('[instancias/create] falha ao preparar IA do profissional:', e)
  }

  return instancia
})
