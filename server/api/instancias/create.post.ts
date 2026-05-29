
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

  const body = await readBody<{ nome_instancia: string }>(event)
  const nome = body?.nome_instancia?.trim()
  if (!nome) {
    throw createError({ statusCode: 400, statusMessage: 'nome_instancia é obrigatório' })
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
      status: 'disconnected'
    })
  })

  return instancia
})
