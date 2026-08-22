// GET /api/relatorios/atendimento-diario?dias=30
// Série diária (mensagens recebidas, atendimentos fechados, TMPR médio) pros
// gráficos de Atendimento — agregada no banco via RPC, um ponto por dia, sem
// buraco (dia sem dado vem com 0/null).
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const query = getQuery(event)
  const dias = Math.min(Math.max(parseInt(String(query.dias || '30'), 10) || 30, 1), 365)

  return await supabaseFetch(event, '/rpc/get_metricas_atendimento_diario', {
    method: 'POST',
    body: JSON.stringify({ p_usuario_id: user.id, p_dias: dias })
  })
})
