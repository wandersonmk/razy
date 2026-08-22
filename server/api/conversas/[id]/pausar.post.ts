// POST /api/conversas/:id/pausar
// Body: { minutos: number } — pausa MANUAL, tem prioridade sobre a automática
// (webhook nunca a sobrescreve). Chama o ai-service pra valer de verdade (é lá
// que a IA consulta o Redis) e espelha em `conversas` só pro badge do painel.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const body = await readBody<{ minutos?: number }>(event)
  const minutos = Math.max(1, Math.floor(Number(body?.minutos) || 0))
  if (!minutos) throw createError({ statusCode: 400, statusMessage: 'minutos é obrigatório' })

  const config = useRuntimeConfig()
  if (!config.aiServiceUrl || !config.internalToken) {
    throw createError({ statusCode: 503, statusMessage: 'ai-service não configurado' })
  }

  const conversas = await supabaseFetch(event, `/conversas?id=eq.${id}&select=id,numero,instancia_id`)
  const conversa = conversas[0]
  if (!conversa) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })
  if (!conversa.instancia_id) throw createError({ statusCode: 400, statusMessage: 'Conversa sem instância vinculada' })

  const baseUrl = String(config.aiServiceUrl).replace(/\/$/, '')
  const res = await fetch(`${baseUrl}/conversas/pausar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Internal-Token': config.internalToken as string },
    body: JSON.stringify({
      usuario_id: user.id,
      instancia_id: conversa.instancia_id,
      telefone: conversa.numero,
      minutos
    })
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({} as any))
    throw createError({ statusCode: res.status, statusMessage: data?.detail || 'Erro ao pausar no ai-service' })
  }

  const [atualizado] = await supabaseFetch(event, `/conversas?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ tempo_pausa: minutos * 60, tempo_pausa_inicio: new Date().toISOString() })
  })

  return atualizado
})
