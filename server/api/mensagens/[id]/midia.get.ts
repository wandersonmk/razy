// GET /api/mensagens/:id/midia
// Busca a mídia (se houver) de UMA mensagem — usado quando a mensagem chega via
// Realtime (o broadcast do banco manda só a linha crua de `mensagens`, sem o
// embed de `midias_conversas` que o fetch inicial da lista traz) e o front
// precisa completar o storage_path pra gerar a signed URL.
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const rows = await supabaseFetch(
    event,
    `/midias_conversas?mensagem_id=eq.${id}&select=id,tipo,storage_path,url_storage&limit=1`
  ) as any[]

  return rows[0] || null
})
