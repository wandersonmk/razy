
// POST /api/instancias/:id/connect — chama UAzAPI /instance/connect, retorna QR
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const config = useRuntimeConfig()
  const instancias = await supabaseFetch(event, `/instancias?id=eq.${id}&select=*`)
  const inst = instancias[0]
  if (!inst) throw createError({ statusCode: 404, statusMessage: 'Instância não encontrada' })
  if (!inst.uazapi_token) {
    throw createError({ statusCode: 400, statusMessage: 'Instância sem token UAzAPI' })
  }

  const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')
  const body = await readBody<{ systemName?: string }>(event).catch(() => ({} as any))

  const response = await fetch(`${baseUrl}/instance/connect`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'token': inst.uazapi_token
    },
    body: JSON.stringify({
      browser: 'auto',
      systemName: body?.systemName || 'Razy'
    })
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
  const loggedIn = !!(data as any)?.loggedIn

  const novoStatus = connected ? 'connected' : 'qr'
  const phone = instance.owner || inst.phone

  await supabaseFetch(event, `/instancias?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: novoStatus, phone })
  }).catch(() => null)

  return { qrcode, paircode, connected, loggedIn, status: novoStatus, phone }
})
