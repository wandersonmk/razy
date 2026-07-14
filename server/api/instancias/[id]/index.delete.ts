
// DELETE /api/instancias/:id — remove a instância na UAzAPI e apaga do banco
// SEM deixar nenhum vínculo (a instância some de todos os canais/registros).
export default defineEventHandler(async (event) => {
  await requireUser(event)
  const id = getRouterParam(event, 'id')
  if (!id) throw createError({ statusCode: 400, statusMessage: 'id obrigatório' })

  const config = useRuntimeConfig()
  const instancias = await supabaseFetch(event, `/instancias?id=eq.${id}&select=*`)
  const inst = instancias[0]
  if (!inst) throw createError({ statusCode: 404, statusMessage: 'Instância não encontrada' })

  // ── TRAVA: não excluir canal que faz parte de campanha EM ANDAMENTO ──────────
  // Excluir a instância no meio de um disparo a tira do roteamento e deixa
  // resíduo (canal-fantasma que a campanha ainda tenta usar). O certo para
  // "trocar o número" é DESCONECTAR e conectar outro NESTA MESMA instância —
  // sem excluir. Só bloqueamos campanhas 'em_andamento'; pausadas/concluídas
  // liberam a exclusão.
  const emUso: string[] = []

  // (a) Campanha de canal único apontando para esta instância.
  const canalUnico = await supabaseFetch(
    event,
    `/campanhas?canal_id=eq.${id}&status=eq.em_andamento&select=id,nome`
  )
  for (const c of canalUnico as any[]) emUso.push(c.nome || c.id)

  // (b) Campanha multi-canal (roteamento/alternância) usa TODOS os canais
  //     conectados do usuário — este canal participa se for elegível a disparo
  //     (tem token e não é de uso exclusivo de notificação).
  const elegivelDisparo = !!inst.uazapi_token && !inst.uso_notificacao
  if (elegivelDisparo) {
    const multi = await supabaseFetch(
      event,
      `/campanhas?usuario_id=eq.${inst.usuario_id}&status=eq.em_andamento&or=(usar_roteamento.is.true,alternar_canais.is.true)&select=id,nome`
    )
    for (const c of multi as any[]) emUso.push(c.nome || c.id)
  }

  if (emUso.length) {
    const lista = [...new Set(emUso)].join(', ')
    throw createError({
      statusCode: 409,
      statusMessage: 'Canal em uso por campanha em andamento',
      message:
        `Este canal não pode ser excluído porque faz parte de campanha em andamento (${lista}). ` +
        `Para trocar o número, use "Desconectar" e conecte outro número nesta mesma instância — ` +
        `assim a campanha continua e não fica resíduo no roteamento. ` +
        `Se realmente precisar excluir, pause ou conclua a campanha antes.`
    })
  }

  // 1) Remove a instância na UAzAPI (desconecta o aparelho e apaga do lado deles).
  if (inst.uazapi_token) {
    const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')
    await fetch(`${baseUrl}/instance`, {
      method: 'DELETE',
      headers: { 'Accept': 'application/json', 'token': inst.uazapi_token }
    }).catch(() => null)
  }

  // 2) Remove TODO vínculo no banco ANTES de apagar a instância:
  //    - followup_disparos.canal_id: FK NO ACTION → bloquearia o DELETE; zera antes.
  //    - campanhas.canal_id: uuid sem FK → zera para não restar vínculo fantasma.
  //    (disparos.canal_id, campanha_logs.canal_id e campanhas.instancia_id têm
  //     FK ON DELETE SET NULL e são limpos automaticamente pelo DELETE abaixo.)
  await supabaseFetch(event, `/followup_disparos?canal_id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ canal_id: null })
  })
  await supabaseFetch(event, `/campanhas?canal_id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ canal_id: null })
  })

  // 3) Apaga a instância de vez.
  await supabaseFetch(event, `/instancias?id=eq.${id}`, { method: 'DELETE' })
  return { ok: true }
})
