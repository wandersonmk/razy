// DELETE /api/profissionais/:id
// Remove o profissional E tudo que é dele: o assistente (assistentes_profissionais
// já tem ON DELETE CASCADE — cai sozinho) e o canal, esse por código: chama a
// UAzAPI pra desconectar/apagar o aparelho e desativa a instância no banco.
//
// O que NUNCA é apagado: `conversas`, `mensagens` e o cliente que aparece em
// Conversas/Clientes via Profissionais. Isso é proposital — o dono da empresa
// quer manter o histórico de atendimento mesmo depois de o profissional sair.
// As colunas que apontavam pro profissional (assigned_to_professional_id,
// enviado_por_profissional_id, conversa_atendentes_historico.profissional_id)
// não têm ON DELETE CASCADE nem SET NULL — sem soltar essas referências ANTES,
// o DELETE do profissional falharia com erro de foreign key. Zeradas, o front
// já trata a ausência como "Profissional removido".
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })
  }

  // Busca a instância ANTES de mexer em qualquer coisa — depois de apagar o
  // profissional o vínculo se perde (instancias.profissional_id vira null,
  // ON DELETE SET NULL).
  const instancias = await supabaseFetch(event, `/instancias?profissional_id=eq.${id}&status=neq.deleted&select=*`)
  const inst = instancias[0] || null

  // Campanha em andamento usando o canal ainda trava — perder o canal no meio
  // de um disparo ativo é um problema operacional, não só de histórico.
  if (inst) {
    const erro = await checarInstanciaPodeSerExcluida(event, inst)
    if (erro) {
      throw createError({ statusCode: 409, statusMessage: 'Profissional não pode ser excluído', message: erro })
    }
  }

  // Solta as referências que bloqueariam o DELETE (RESTRICT por padrão) —
  // as linhas continuam no banco, só perdem o vínculo vivo com o profissional.
  await supabaseFetch(event, `/conversas?assigned_to_professional_id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ assigned_to_professional_id: null })
  })
  await supabaseFetch(event, `/mensagens?enviado_por_profissional_id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ enviado_por_profissional_id: null })
  })
  // profissional_nome_snapshot já guarda o nome pra sempre — só solta a FK.
  await supabaseFetch(event, `/conversa_atendentes_historico?profissional_id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ profissional_id: null })
  })

  await supabaseFetch(event, `/profissionais?id=eq.${id}`, {
    method: 'DELETE',
    headers: { Prefer: 'return=minimal' }
  })

  // Profissional já foi embora (e o assistente junto, via cascade). Agora
  // desativa o canal — best-effort: se isso falhar, o profissional já não
  // existe mais, mas a instância órfã ainda pode ser desativada manualmente
  // em Profissionais & Canais.
  if (inst) {
    await apagarInstanciaNaUazapiEDesativar(event, inst).catch(() => null)
  }

  return { ok: true }
})
