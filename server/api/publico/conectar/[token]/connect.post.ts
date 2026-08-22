// POST /api/publico/conectar/:token/connect — SEM autenticação.
// Espelha /api/instancias/:id/connect, mas resolve a instância pelo token do
// link (RPC instancia_uazapi_token_publico) em vez de exigir usuário logado.
// O uazapi_token NUNCA sai desta função — só é usado aqui pra chamar a UAzAPI.
export default defineEventHandler(async (event) => {
  const token = getRouterParam(event, 'token')
  if (!token) throw createError({ statusCode: 400, statusMessage: 'token obrigatório' })

  const config = useRuntimeConfig()
  const rows = await supabasePublicRpc('instancia_uazapi_token_publico', { p_token: token })
  const row = Array.isArray(rows) ? rows[0] : rows
  if (!row?.uazapi_token) throw createError({ statusCode: 404, statusMessage: 'Link inválido ou revogado' })

  const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')
  const response = await fetch(`${baseUrl}/instance/connect`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'token': row.uazapi_token
    },
    body: JSON.stringify({ browser: 'auto', systemName: 'Razy' })
  })

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw createError({
      statusCode: response.status,
      statusMessage: (data as any)?.response || (data as any)?.message || `HTTP ${response.status}`
    })
  }

  const instance = (data as any)?.instance || {}
  const qrcode = instance.qrcode || (data as any)?.qrcode || null
  const paircode = instance.paircode || (data as any)?.paircode || null
  const instanceStatus = String(instance.status || '').toLowerCase()
  const connected = !!(data as any)?.connected || instanceStatus === 'connected'
  const novoStatus = connected ? 'connected' : 'qr'
  const phone = instance.owner || null

  await supabasePublicRpc('instancia_atualizar_status_publica', {
    p_token: token, p_status: novoStatus, p_phone: phone
  }).catch(() => null)

  return { qrcode, paircode, connected, status: novoStatus, phone }
})
