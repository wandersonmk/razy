
export default defineEventHandler(async (event) => {
  await requireUser(event)

  const config = useRuntimeConfig()
  if (!config.uazapiToken) {
    return { ok: false, erro: 'Token não configurado no servidor' }
  }

  const url = `${String(config.uazapiUrl).replace(/\/$/, '')}/instance/status`

  try {
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'token': config.uazapiToken
      }
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      return { ok: false, erro: (data as any)?.message || `HTTP ${response.status}` }
    }

    return { ok: true, status: (data as any)?.status || (data as any)?.instance?.status, raw: data }
  } catch (err: any) {
    return { ok: false, erro: err?.message || 'Erro de rede' }
  }
})
