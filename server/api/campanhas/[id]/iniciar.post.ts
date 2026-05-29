// POST /api/campanhas/[id]/iniciar
// "Porteiro": valida o usuário logado e a posse da campanha, e repassa o disparo
// para o ai-service adicionando o INTERNAL_TOKEN (que nunca vai ao navegador).
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const config = useRuntimeConfig()
  const id = getRouterParam(event, 'id')

  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id da campanha é obrigatório' })
  }
  if (!config.aiServiceUrl || !config.internalToken) {
    throw createError({
      statusCode: 503,
      statusMessage: 'ai-service não configurado (defina AI_SERVICE_URL e INTERNAL_TOKEN)'
    })
  }

  // Garante que a campanha existe e pertence ao usuário logado.
  const campanhas = await supabaseFetch(
    event,
    `/campanhas?id=eq.${id}&select=id,usuario_id,canal_id,status`
  )
  const campanha = campanhas[0]
  if (!campanha) {
    throw createError({ statusCode: 404, statusMessage: 'Campanha não encontrada' })
  }
  if (campanha.usuario_id !== user.id) {
    throw createError({ statusCode: 403, statusMessage: 'Sem permissão sobre esta campanha' })
  }
  if (!campanha.canal_id) {
    throw createError({ statusCode: 400, statusMessage: 'Campanha sem canal vinculado' })
  }

  const baseUrl = String(config.aiServiceUrl).replace(/\/$/, '')
  const res = await fetch(`${baseUrl}/campanhas/${id}/iniciar`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-Internal-Token': config.internalToken as string
    }
  })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw createError({
      statusCode: res.status,
      statusMessage: (data as any)?.detail || (data as any)?.message || 'Erro ao iniciar disparo no ai-service'
    })
  }
  return data
})
