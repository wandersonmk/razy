// POST /api/conversas/:id/marcar-lida
// Zera o contador de não lidas de verdade no banco — chamado quando o dono
// abre a conversa no painel (e de novo se chegar mensagem nova enquanto ela
// já está aberta). Sem isso o zero era só local (em memória): ao trocar de
// aba/página e voltar, a lista recarregava do banco com o contador antigo e
// o badge "voltava".
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id é obrigatório' })

  const atualizado = await supabaseFetch(event, `/conversas?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ nao_lidas: 0 })
  }) as any[]

  if (!atualizado?.length) throw createError({ statusCode: 404, statusMessage: 'Conversa não encontrada' })
  return atualizado[0]
})
