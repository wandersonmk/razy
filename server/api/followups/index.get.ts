// GET /api/followups — lista configs de follow-up do usuário com etapas e campanha
export default defineEventHandler(async (event) => {
  const user = await requireUser(event)
  const configs = await supabaseFetch(
    event,
    `/followup_configs?usuario_id=eq.${user.id}&select=id,campanha_id,ativo,criado_em,campanha:campanhas(id,nome,status,total_enviados)&order=criado_em.desc`
  )
  // Busca etapas para cada config
  const result = await Promise.all(
    (configs || []).map(async (c: any) => {
      const etapas = await supabaseFetch(
        event,
        `/followup_etapas?config_id=eq.${c.id}&order=ordem.asc`
      )
      return { ...c, etapas: etapas || [] }
    })
  )
  return result
})
