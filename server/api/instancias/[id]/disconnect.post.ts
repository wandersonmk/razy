
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const config = useRuntimeConfig()
  const instancias = await supabaseFetch(event, `/instancias?id=eq.${id}&select=*`)
  const inst = instancias[0]
  if (!inst) throw createError({ statusCode: 404, statusMessage: 'Instância não encontrada' })

  if (inst.uazapi_token) {
    const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')
    await fetch(`${baseUrl}/instance/disconnect`, {
      method: 'POST',
      headers: { 'Accept': 'application/json', 'token': inst.uazapi_token }
    }).catch(() => null)
  }

  await supabaseFetch(event, `/instancias?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'disconnected' })
  })

  return { ok: true }
})
