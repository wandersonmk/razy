// GET /api/conversas/:id/mensagens
// Histórico da conversa, com a mídia (se houver) já embutida via midias_conversas.
// Query: before=<iso date> (pagina pra trás), limit=<n>
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const query = getQuery(event)
  const limit = Math.min(Math.max(parseInt(String(query.limit || '50'), 10) || 50, 1), 200)
  const before = query.before ? String(query.before) : null

  const filtros = [`conversa_id=eq.${id}`]
  if (before) filtros.push(`data_hora=lt.${before}`)

  const select = 'select=*,midia:midias_conversas(id,tipo,storage_path,url_storage)'
  // Busca as mais recentes primeiro (pra paginar "carregar mais antigas"),
  // devolve em ordem cronológica pro front só dar append no topo.
  const mensagens = await supabaseFetch(
    event,
    `/mensagens?${filtros.join('&')}&${select}&order=data_hora.desc&limit=${limit}`
  ) as any[]

  return mensagens.reverse()
})
