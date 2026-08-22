import type { H3Event } from 'h3'

// Única checagem que ainda faz sentido antes de excluir um canal: campanha
// EM ANDAMENTO que depende dele. Perder histórico não é mais motivo de bloqueio
// (ver `apagarInstanciaNaUazapiEDesativar` — não apaga conversas/mensagens,
// só desativa o canal), mas tirar um canal no meio de um disparo ativo quebra
// o roteamento na hora. Retorna uma mensagem de erro, ou null se pode seguir.
export async function checarInstanciaPodeSerExcluida(event: H3Event, inst: any): Promise<string | null> {
  const id = inst.id
  const emUso: string[] = []

  const canalUnico = await supabaseFetch(event, `/campanhas?canal_id=eq.${id}&status=eq.em_andamento&select=id,nome`)
  for (const c of canalUnico as any[]) emUso.push(c.nome || c.id)

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
    return (
      `Este canal não pode ser excluído porque faz parte de campanha em andamento (${lista}). ` +
      `Para trocar o número, use "Desconectar" e conecte outro número nesta mesma instância — ` +
      `assim a campanha continua e não fica resíduo no roteamento. ` +
      `Se realmente precisar excluir, pause ou conclua a campanha antes.`
    )
  }

  return null
}

// Desconecta/apaga o aparelho na UAzAPI e DESATIVA a instância no banco —
// nunca apaga a linha. `conversas`/`mensagens`/`midias_conversas` referenciam
// instancia_id sem ON DELETE (RESTRICT); apagar de verdade quebraria com erro
// de foreign key sempre que o canal já tivesse alguma conversa. Marcando
// status='deleted' (já é o valor que o resto do app espera pra "canal morto"
// — ver índice único parcial e o filtro em create.post.ts/index.get.ts) o
// histórico continua intacto e consultável, só o canal some da UI/roteamento.
export async function apagarInstanciaNaUazapiEDesativar(event: H3Event, inst: any): Promise<void> {
  const id = inst.id
  const config = useRuntimeConfig()

  if (inst.uazapi_token) {
    const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')
    await fetch(`${baseUrl}/instance`, {
      method: 'DELETE',
      headers: { 'Accept': 'application/json', 'token': inst.uazapi_token }
    }).catch(() => null)
  }

  await supabaseFetch(event, `/instancias?id=eq.${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'deleted', uazapi_token: null })
  })
}
