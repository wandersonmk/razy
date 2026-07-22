// Conta as respostas REAIS por campanha: contatos DISTINTOS que responderam
// (disparos.respondido_em != null). Uma resposta por cliente, não por mensagem.
//
// Usado no lugar do contador denormalizado `campanhas.total_respostas`, que pode
// dessincronizar (inflou antes da trava de "1ª resposta"; não diminui ao excluir
// um contato). Aqui o número é sempre derivado da fonte da verdade.
//
// A contagem roda NO BANCO (RPC `contar_respostas_campanhas`). A versão anterior
// baixava as linhas de `disparos` e agregava no navegador — mas o PostgREST corta
// a resposta em 1000 linhas por padrão, e a base já passou disso. O corte pegava
// as campanhas mais novas, que apareciam com menos respostas do que tinham (ou
// zero) enquanto as antigas batiam certo.
export async function contarRespostasPorCampanha(
  supabase: any,
  campanhaIds: string[]
): Promise<Map<string, number>> {
  const mapa = new Map<string, number>()
  if (!supabase || campanhaIds.length === 0) return mapa

  const { data, error } = await supabase.rpc('contar_respostas_campanhas', { ids: campanhaIds })

  if (!error && data) {
    for (const r of data) mapa.set((r as any).campanha_id, Number((r as any).total) || 0)
    return mapa
  }

  // Fallback: se a RPC ainda não existe neste ambiente, agrega no cliente —
  // paginando, para não cair no mesmo limite de 1000 linhas de antes.
  return await contarPaginando(supabase, campanhaIds)
}

const PAGINA = 1000

async function contarPaginando(
  supabase: any,
  campanhaIds: string[]
): Promise<Map<string, number>> {
  const sets = new Map<string, Set<string>>()
  for (let inicio = 0; ; inicio += PAGINA) {
    const { data, error } = await supabase
      .from('disparos')
      .select('campanha_id, contato_id')
      .not('respondido_em', 'is', null)
      .in('campanha_id', campanhaIds)
      .order('campanha_id', { ascending: true })
      .range(inicio, inicio + PAGINA - 1)

    if (error || !data || data.length === 0) break

    for (const r of data) {
      const cid = (r as any).campanha_id
      if (!sets.has(cid)) sets.set(cid, new Set())
      sets.get(cid)!.add((r as any).contato_id)
    }
    if (data.length < PAGINA) break
  }

  const mapa = new Map<string, number>()
  for (const [cid, s] of sets) mapa.set(cid, s.size)
  return mapa
}
