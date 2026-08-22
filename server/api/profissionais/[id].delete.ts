// DELETE /api/profissionais/:id
// Remove o profissional E tudo que é dele: o assistente (assistentes_profissionais
// já tem ON DELETE CASCADE — cai sozinho) e a instância/canal, essa por
// código: chama a UAzAPI pra desconectar/apagar o aparelho e depois remove do
// banco. Se o profissional (ou o canal dele) já tem histórico de conversa,
// a exclusão inteira é recusada — proteção contra perder rastro de atendimento.
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })
  }

  // Busca a instância ANTES de mexer em qualquer coisa — depois de apagar o
  // profissional o vínculo se perde (instancias.profissional_id vira null).
  const instancias = await supabaseFetch(event, `/instancias?profissional_id=eq.${id}&select=*`)
  const inst = instancias[0] || null

  if (inst) {
    const erro = await checarInstanciaPodeSerExcluida(event, inst)
    if (erro) {
      throw createError({ statusCode: 409, statusMessage: 'Profissional não pode ser excluído', message: erro })
    }
  }

  try {
    await supabaseFetch(event, `/profissionais?id=eq.${id}`, {
      method: 'DELETE',
      headers: { Prefer: 'return=minimal' }
    })
  } catch (e: any) {
    if (e?.statusCode === 409 || /foreign key/i.test(e?.statusMessage || '')) {
      throw createError({
        statusCode: 409,
        statusMessage: 'Este profissional já tem conversas/atendimentos registrados e não pode ser excluído. Desative-o em vez de excluir.'
      })
    }
    throw e
  }

  // Profissional já foi embora (e o assistente junto, via cascade). Agora
  // apaga o canal — best-effort: se isso falhar, o profissional já não
  // existe mais, mas a instância órfã ainda pode ser excluída manualmente
  // em Profissionais & Canais.
  if (inst) {
    await apagarInstanciaNaUazapiEBanco(event, inst).catch(() => null)
  }

  return { ok: true }
})
