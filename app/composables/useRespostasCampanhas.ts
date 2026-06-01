// Conta as respostas REAIS por campanha: contatos DISTINTOS que responderam
// (disparos.respondido_em != null). Uma resposta por cliente, não por mensagem.
//
// Usado no lugar do contador denormalizado `campanhas.total_respostas`, que pode
// dessincronizar (inflou antes da trava de "1ª resposta"; não diminui ao excluir
// um contato). Aqui o número é sempre derivado da fonte da verdade.
export async function contarRespostasPorCampanha(
  supabase: any,
  campanhaIds: string[]
): Promise<Map<string, number>> {
  const mapa = new Map<string, number>()
  if (!supabase || campanhaIds.length === 0) return mapa

  const { data, error } = await supabase
    .from('disparos')
    .select('campanha_id, contato_id')
    .not('respondido_em', 'is', null)
    .in('campanha_id', campanhaIds)

  if (error || !data) return mapa

  const sets = new Map<string, Set<string>>()
  for (const r of data) {
    const cid = (r as any).campanha_id
    if (!sets.has(cid)) sets.set(cid, new Set())
    sets.get(cid)!.add((r as any).contato_id)
  }
  for (const [cid, s] of sets) mapa.set(cid, s.size)
  return mapa
}
