// GET /api/conversas/:id/mensagens
// Histórico da conversa, com a mídia (se houver) já embutida via midias_conversas.
// Query: before=<iso date> + before_id=<uuid> (cursor pra paginar pra trás), limit=<n>
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const query = getQuery(event)
  const limit = Math.min(Math.max(parseInt(String(query.limit || '50'), 10) || 50, 1), 200)
  const before = query.before ? String(query.before) : null
  const beforeId = query.before_id ? String(query.before_id) : null

  const filtros = [`conversa_id=eq.${id}`]
  if (before) {
    // Cursor por (data_hora, id), não só data_hora: o campo é gravado com
    // now() (microssegundos), mas empate ainda é possível — import em lote,
    // duas mensagens na mesma transação. Sem desempate por id, a página
    // seguinte pula/duplica mensagem em silêncio (mesma categoria do
    // order(created_at).order(id) usado em Clientes — ver
    // carregamento-mensagens-e-filtros.md). encodeURIComponent porque o
    // timestamp volta com "+00:00": um "+" cru na query string vira espaço
    // em parsers baseados em x-www-form-urlencoded (gotcha comum do
    // PostgREST) e quebraria o filtro de data.
    const beforeEnc = encodeURIComponent(before)
    filtros.push(
      beforeId
        ? `or=(data_hora.lt.${beforeEnc},and(data_hora.eq.${beforeEnc},id.lt.${encodeURIComponent(beforeId)}))`
        : `data_hora=lt.${beforeEnc}`
    )
  }

  const select = 'select=*,midia:midias_conversas(id,tipo,storage_path,url_storage)'
  // Busca as mais recentes primeiro (pra paginar "carregar mais antigas"),
  // devolve em ordem cronológica pro front só dar append no topo. Desempate
  // por id garante ordem estável mesmo quando duas mensagens empatam em
  // data_hora.
  const mensagens = await supabaseFetch(
    event,
    `/mensagens?${filtros.join('&')}&${select}&order=data_hora.desc,id.desc&limit=${limit}`
  ) as any[]

  return mensagens.reverse()
})
