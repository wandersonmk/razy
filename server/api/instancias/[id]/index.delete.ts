
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
