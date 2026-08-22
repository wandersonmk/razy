import type { H3Event } from 'h3'

// Checa se a instância PODE ser excluída de vez (UAzAPI + banco). Retorna uma
// mensagem de erro (string) se não puder, ou null se estiver liberado.
// Usado tanto por DELETE /api/instancias/:id quanto pelo cascade ao excluir
// um profissional — as duas travas têm que valer nos dois caminhos.
export async function checarInstanciaPodeSerExcluida(event: H3Event, inst: any): Promise<string | null> {
  const id = inst.id

  // ── TRAVA 1: canal em uso por campanha EM ANDAMENTO ──────────────────────
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

  // ── TRAVA 2: canal com histórico de conversa/atendimento ─────────────────
  // conversas.instancia_id, mensagens.instancia_id e midias_conversas.instancia_id
  // não têm ON DELETE — apagar a instância sem checar isso quebra com um erro
  // cru de foreign key. Melhor bloquear com uma mensagem clara.
  const [conversa] = await supabaseFetch(event, `/conversas?instancia_id=eq.${id}&select=id&limit=1`)
  if (conversa) {
    return 'Este canal já tem conversas/atendimentos registrados e não pode ser excluído. Desconecte-o em vez de excluir — o histórico continua acessível em Conversas.'
  }

  return null
}

// Apaga a instância na UAzAPI e no banco. Só chamar DEPOIS de
// `checarInstanciaPodeSerExcluida` retornar null — não repete as checagens.
export async function apagarInstanciaNaUazapiEBanco(event: H3Event, inst: any): Promise<void> {
  const id = inst.id
  const config = useRuntimeConfig()

  // 1) Remove a instância na UAzAPI (desconecta o aparelho e apaga do lado deles).
  if (inst.uazapi_token) {
    const baseUrl = String(config.uazapiUrl).replace(/\/$/, '')
    await fetch(`${baseUrl}/instance`, {
      method: 'DELETE',
      headers: { 'Accept': 'application/json', 'token': inst.uazapi_token }
    }).catch(() => null)
  }

  // 2) Remove todo vínculo que bloquearia o DELETE ou ficaria fantasma.
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
}
