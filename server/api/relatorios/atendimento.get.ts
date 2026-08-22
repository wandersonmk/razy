// GET /api/relatorios/atendimento?dias=30
// Métricas por profissional (canal por profissional): mensagens recebidas,
// mensagens enviadas, atendimentos (por opened_at — automático) e tempo até
// 1ª resposta. Agregado no banco via RPC (public.get_metricas_atendimento) —
// nunca soma no navegador, porque o PostgREST corta em 1000 linhas por padrão.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const query = getQuery(event)
  const dias = Math.min(Math.max(parseInt(String(query.dias || '30'), 10) || 30, 1), 365)

  const fim = new Date()
  const inicio = new Date(fim.getTime() - dias * 24 * 60 * 60 * 1000)

  const resultado = await supabaseFetch(event, '/rpc/get_metricas_atendimento', {
    method: 'POST',
    body: JSON.stringify({
      p_usuario_id: user.id,
      p_inicio: inicio.toISOString(),
      p_fim: fim.toISOString()
    })
  })

  return resultado
})
