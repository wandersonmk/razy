// GET /api/instancias
// Lista as instâncias do usuário e sincroniza status/phone com a UAzAPI em paralelo.
// Shape esperado da UAzAPI /instance/status:
//   { instance: { status, owner, ... }, status: { connected, loggedIn, jid } }
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const config = useRuntimeConfig()
  const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')

  const instancias = await supabaseFetch(
    event,
    `/instancias?usuario_id=eq.${user.id}&status=neq.deleted&select=*&order=created_at.desc`
  )

  const atualizadas = await Promise.all(
    (instancias as any[]).map(async (inst) => {
      if (!inst.uazapi_token) return inst
      try {
        const res = await fetch(`${baseUrl}/instance/status`, {
          headers: { 'Accept': 'application/json', 'token': inst.uazapi_token }
        })
        if (!res.ok) return inst
        const data = await res.json().catch(() => ({} as any))

        const instance = (data as any)?.instance || {}
        const statusObj = (data as any)?.status && typeof (data as any).status === 'object'
          ? (data as any).status
          : null
        const instanceStatusStr = String(instance.status || (typeof (data as any)?.status === 'string' ? (data as any).status : '')).toLowerCase()
        const phone = instance.owner || (data as any)?.phone || inst.phone

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
          await supabaseFetch(event, `/instancias?id=eq.${inst.id}`, {
            method: 'PATCH',
            body: JSON.stringify({ status: novoStatus, phone })
          }).catch(() => null)
          return { ...inst, status: novoStatus, phone }
        }
        return inst
      } catch {
        return inst
      }
    })
  )

  return atualizadas
})
