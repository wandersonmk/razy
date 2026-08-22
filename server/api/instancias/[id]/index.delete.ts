
// DELETE /api/instancias/:id — remove a instância na UAzAPI e apaga do banco
// SEM deixar nenhum vínculo (a instância some de todos os canais/registros).
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const instancias = await supabaseFetch(event, `/instancias?id=eq.${id}&select=*`)
  const inst = instancias[0]
  if (!inst) throw createError({ statusCode: 404, statusMessage: 'Instância não encontrada' })

  const erro = await checarInstanciaPodeSerExcluida(event, inst)
  if (erro) throw createError({ statusCode: 409, statusMessage: 'Canal não pode ser excluído', message: erro })

  await apagarInstanciaNaUazapiEBanco(event, inst)
  return { ok: true }
})
