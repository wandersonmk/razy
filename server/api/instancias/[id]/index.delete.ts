
// DELETE /api/instancias/:id — desconecta/remove o aparelho na UAzAPI e
// desativa a instância no banco (status='deleted'; a linha continua existindo
// pra não quebrar conversas/mensagens que já referenciam esse instancia_id).
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const instancias = await supabaseFetch(event, `/instancias?id=eq.${id}&select=*`)
  const inst = instancias[0]
  if (!inst) throw createError({ statusCode: 404, statusMessage: 'Instância não encontrada' })

  const erro = await checarInstanciaPodeSerExcluida(event, inst)
  if (erro) throw createError({ statusCode: 409, statusMessage: 'Canal não pode ser excluído', message: erro })

  await apagarInstanciaNaUazapiEDesativar(event, inst)
  return { ok: true }
})
