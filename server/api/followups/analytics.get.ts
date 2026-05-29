// GET /api/followups/analytics?campanha_id=  (campanha_id opcional → todas)
// Retorna métricas agregadas + histórico recente de follow-ups do usuário.
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const q = getQuery(event)
  const campanhaId = q.campanha_id ? String(q.campanha_id) : null

  const filtroCampanha = campanhaId ? `&campanha_id=eq.${campanhaId}` : ''

  // Métricas (agrega em JS — Supabase REST não soma por status facilmente)
  const statusRows: any[] = await supabaseFetch(
    event,
    `/followup_disparos?usuario_id=eq.${user.id}${filtroCampanha}&select=status`
  )
  const lista = statusRows || []
  const metricas = {
    total:       lista.length,
    enviados:    lista.filter((d) => d.status === 'enviado').length,
    responderam: lista.filter((d) => d.status === 'respondeu').length,
    pendentes:   lista.filter((d) => d.status === 'pendente').length,
    cancelados:  lista.filter((d) => d.status === 'cancelado').length,
  }

  // Histórico recente (até 100), com contato, etapa e campanha
  const historico: any[] = await supabaseFetch(
    event,
    `/followup_disparos?usuario_id=eq.${user.id}${filtroCampanha}` +
    `&select=id,status,agendado_para,enviado_em,mensagem_enviada,` +
    `contato:contatos(nome,telefone),etapa:followup_etapas(ordem),campanha:campanhas(nome)` +
    `&order=criado_em.desc&limit=100`
  )

  return { metricas, historico: historico || [] }
})
