// GET /api/instancias/:id/status
// Consulta UAzAPI /instance/status, normaliza o resultado, salva phone+status no DB.
// Shape esperado da UAzAPI:
//   { instance: { status, owner, profileName, ... }, status: { connected, loggedIn, jid } }
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const config = useRuntimeConfig()
  const instancias = await supabaseFetch(event, `/instancias?id=eq.${id}&select=*`)
  const inst = instancias[0]
  if (!inst) throw createError({ statusCode: 404, statusMessage: 'Instância não encontrada' })
  if (!inst.uazapi_token) return { status: inst.status, phone: inst.phone, connected: false }

  const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')
  const response = await fetch(`${baseUrl}/instance/status`, {
    headers: { 'Accept': 'application/json', 'token': inst.uazapi_token }
  })
  const data = await response.json().catch(() => ({} as any))

  if (!response.ok) {
    return { status: inst.status, phone: inst.phone, connected: false, erro: (data as any)?.message || `HTTP ${response.status}` }
  }

  const instance = (data as any)?.instance || {}
  const statusObj = (data as any)?.status && typeof (data as any).status === 'object'
    ? (data as any).status
    : null
  const instanceStatusStr = String(instance.status || (typeof (data as any)?.status === 'string' ? (data as any).status : '')).toLowerCase()
  const phone = instance.owner || (data as any)?.phone || inst.phone

  // Boolean autoritativo da UAzAPI vence sobre a string meta.
  // Cuidado: "disconnected" contém "connect" como substring.
  let novoStatus: string = inst.status
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

  if (novoStatus !== inst.status || phone !== inst.phone) {
    await supabaseFetch(event, `/instancias?id=eq.${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: novoStatus, phone })
    }).catch(() => null)
  }

  return { status: novoStatus, phone, connected: novoStatus === 'connected' }
})
