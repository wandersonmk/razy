// GET /api/publico/conectar/:token/poll — SEM autenticação.
// Espelha /api/instancias/:id/status (mesma lógica de leitura do status real
// na UAzAPI — ver comentário lá sobre por que `status.connected`/`loggedIn`
// manda mais que a string `instance.status`), resolvendo pelo token do link.
export default defineEventHandler(async (event) => {
  const token = getRouterParam(event, 'token')
  if (!token) throw createError({ statusCode: 400, statusMessage: 'token obrigatório' })

  const config = useRuntimeConfig()
  const rows = await supabasePublicRpc('instancia_uazapi_token_publico', { p_token: token })
  const row = Array.isArray(rows) ? rows[0] : rows
  if (!row?.uazapi_token) throw createError({ statusCode: 404, statusMessage: 'Link inválido ou revogado' })

  const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')
  const response = await fetch(`${baseUrl}/instance/status`, {
    headers: { 'Accept': 'application/json', 'token': row.uazapi_token }
  })
  const data = await response.json().catch(() => ({} as any))

  if (!response.ok) {
    return { status: 'qr', connected: false, erro: (data as any)?.message || `HTTP ${response.status}` }
  }

  const instance = (data as any)?.instance || {}
  const statusObj = (data as any)?.status && typeof (data as any).status === 'object'
    ? (data as any).status
    : null
  const instanceStatusStr = String(instance.status || (typeof (data as any)?.status === 'string' ? (data as any).status : '')).toLowerCase()
  const phone = instance.owner || (data as any)?.phone || null

  let novoStatus = 'qr'
  if (statusObj && typeof statusObj.connected === 'boolean') {
    if (statusObj.connected || statusObj.loggedIn) novoStatus = 'connected'
    else if (instanceStatusStr.includes('qr')) novoStatus = 'qr'
    else novoStatus = 'disconnected'
  } else if (instanceStatusStr.includes('disconnect') || instanceStatusStr.includes('offline')) {
    novoStatus = 'disconnected'
  } else if (instanceStatusStr === 'connected' || instanceStatusStr === 'online') {
    novoStatus = 'connected'
  } else if (instanceStatusStr.includes('qr')) {
    novoStatus = 'qr'
  }

  await supabasePublicRpc('instancia_atualizar_status_publica', {
    p_token: token, p_status: novoStatus, p_phone: phone
  }).catch(() => null)

  return { status: novoStatus, phone, connected: novoStatus === 'connected' }
})
