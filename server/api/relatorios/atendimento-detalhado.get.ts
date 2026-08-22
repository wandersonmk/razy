// GET /api/relatorios/atendimento-detalhado?dias=30
// Detalhe por CONVERSA (cliente) dentro do período — quem o profissional
// atendeu, não só o agregado. Mesma regra de atribuição de
// /api/relatorios/atendimento (dono do canal, não a atribuição manual).
// Agregado no banco via RPC (public.get_atendimentos_detalhado) — nunca soma
// no navegador, porque o PostgREST corta em 1000 linhas por padrão.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const query = getQuery(event)
  const dias = Math.min(Math.max(parseInt(String(query.dias || '30'), 10) || 30, 1), 365)

  const fim = new Date()
  const inicio = new Date(fim.getTime() - dias * 24 * 60 * 60 * 1000)

  const resultado = await supabaseFetch(event, '/rpc/get_atendimentos_detalhado', {
    method: 'POST',
    body: JSON.stringify({
      p_usuario_id: user.id,
      p_inicio: inicio.toISOString(),
      p_fim: fim.toISOString()
    })
  })

  return resultado
})
