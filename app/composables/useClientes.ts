// "Clientes" = contatos que RESPONDERAM a algum disparo (registrado via webhook).
// A fonte é a tabela `disparos` (respondido_em não nulo) + join no contato.

export interface Cliente {
  id: string
  nome: string
  telefone: string
  empresa?: string
  created_at: string          // aqui = data da resposta (respondido_em)
  resposta_texto?: string | null
  campanha_id?: string
  campanha_nome?: string
  pausado_segundos?: number | null
}

// últimos 11 dígitos (normaliza 55 + DDD + número p/ casar telefones de fontes diferentes)
function _chaveTel(t: string): string {
  const d = (t || '').replace(/\D/g, '')
  return d.slice(-11)
}

export interface FiltrosClientes {
  campanha_id?: string
  data_inicio?: string
  data_fim?: string
}

// "Clientes via Profissionais" = contatos que mandaram mensagem pro WhatsApp
// de um profissional (canal por profissional — página Conversas). Fonte é a
// tabela `conversas` (que só existe pra instâncias com profissional_id, ver
// webhook.py), NUNCA `contatos`/`disparos` — são dois universos diferentes,
// por isso duas abas separadas em vez de uma lista só.
export interface ClienteViaProfissional {
  id: string                    // id da conversa
  nome: string
  telefone: string
  profissional_id: string | null
  profissional_nome: string
  ultima_mensagem: string | null
  created_at: string
}

export interface FiltrosClientesProfissionais {
  profissional_id?: string
  data_inicio?: string
  data_fim?: string
}

export const useClientes = () => {
  let supabase: any = null
  if (typeof window !== 'undefined') {
    supabase = useSupabaseClient()
  }

  const clientes = ref<Cliente[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Busca contatos que responderam (1 entrada por contato, a resposta mais recente).
  const fetchClientes = async (filtros?: FiltrosClientes): Promise<void> => {
    if (!supabase) return
    isLoading.value = true
    error.value = null
    try {
      let query = supabase
        .from('disparos')
        .select('contato_id, resposta_texto, respondido_em, campanha_id, campanha:campanhas(id, nome), contato:contatos(id, nome, telefone, empresa)')
        .not('respondido_em', 'is', null)
        .order('respondido_em', { ascending: false })

      if (filtros?.campanha_id) {
        query = query.eq('campanha_id', filtros.campanha_id)
      }
      if (filtros?.data_inicio) {
        query = query.gte('respondido_em', new Date(filtros.data_inicio).toISOString())
      }
      if (filtros?.data_fim) {
        // inclui até o fim do dia selecionado
        const fim = new Date(filtros.data_fim)
        fim.setHours(23, 59, 59, 999)
        query = query.lte('respondido_em', fim.toISOString())
      }

      const { data, error: err } = await query

      if (err) {
        error.value = `Erro ao carregar clientes: ${err.message}`
        return
      }

      // Quando há filtro por campanha, permite o mesmo contato aparecer mais de uma vez
      // (pode ter respondido em campanhas diferentes). Sem filtro, deduplica por contato.
      const vistos = new Set<string>()
      const lista: Cliente[] = []
      for (const d of data || []) {
        const c = (d as any).contato
        if (!c) continue
        const dedupeKey = filtros?.campanha_id ? `${c.id}_${(d as any).campanha_id}` : c.id
        if (vistos.has(dedupeKey)) continue
        vistos.add(dedupeKey)
        lista.push({
          id: c.id,
          nome: c.nome || '—',
          telefone: c.telefone,
          empresa: c.empresa || '',
          created_at: (d as any).respondido_em,
          resposta_texto: (d as any).resposta_texto,
          campanha_id: (d as any).campanha_id,
          campanha_nome: (d as any).campanha?.nome || '—',
        })
      }
      clientes.value = lista

      // Anexa o estado de pausa (Redis via ai-service) por telefone.
      await aplicarPausas()
    } catch (err: any) {
      error.value = 'Erro inesperado ao carregar clientes'
    } finally {
      isLoading.value = false
    }
  }

  const aplicarPausas = async (): Promise<void> => {
    try {
      const sb: any = supabase
      let headers: Record<string, string> = {}
      if (sb) {
        const { data } = await sb.auth.getSession()
        if (data.session?.access_token) headers = { Authorization: `Bearer ${data.session.access_token}` }
      }
      const res = await $fetch<{ pausas: { telefone: string; segundos: number }[] }>('/api/clientes/pausas', { headers })
      const mapa = new Map<string, number>()
      for (const p of res.pausas || []) mapa.set(_chaveTel(p.telefone), p.segundos)
      clientes.value = clientes.value.map((c) => ({
        ...c,
        pausado_segundos: mapa.get(_chaveTel(c.telefone)) ?? null
      }))
    } catch {
      // sem pausas / serviço indisponível — não bloqueia a lista
    }
  }

  const despausar = async (telefone: string): Promise<boolean> => {
    try {
      const sb: any = supabase
      let headers: Record<string, string> = {}
      if (sb) {
        const { data } = await sb.auth.getSession()
        if (data.session?.access_token) headers = { Authorization: `Bearer ${data.session.access_token}` }
      }
      await $fetch('/api/clientes/despausar', { method: 'POST', headers, body: { telefone } })
      const alvo = _chaveTel(telefone)
      clientes.value = clientes.value.map((c) =>
        _chaveTel(c.telefone) === alvo ? { ...c, pausado_segundos: null } : c
      )
      return true
    } catch {
      return false
    }
  }

  // "Clientes" é uma visão derivada dos contatos que responderam. Excluir aqui
  // apaga o CONTATO de vez: some de toda a aplicação (públicos, campanhas, etc.).
  // clienteId é o id do contato. Os `disparos` somem por cascade; os
  // `followup_disparos` não têm cascade (FK NO ACTION), então removemos antes.
  const deleteCliente = async (clienteId: string): Promise<boolean> => {
    if (!supabase) return false
    try {
      const { error: errFollow } = await supabase
        .from('followup_disparos')
        .delete()
        .eq('contato_id', clienteId)
      if (errFollow) throw errFollow

      const { error: errContato } = await supabase
        .from('contatos')
        .delete()
        .eq('id', clienteId)
      if (errContato) throw errContato

      clientes.value = clientes.value.filter((c) => c.id !== clienteId)
      return true
    } catch (err: any) {
      error.value = `Erro ao excluir cliente: ${err?.message || err}`
      return false
    }
  }

  const clearError = (): void => {
    error.value = null
  }

  // ── Clientes via Profissionais ──────────────────────────────────────────
  const clientesProfissionais = ref<ClienteViaProfissional[]>([])
  const isLoadingProfissionais = ref(false)
  const errorProfissionais = ref<string | null>(null)

  const fetchClientesViaProfissionais = async (filtros?: FiltrosClientesProfissionais): Promise<void> => {
    if (!supabase) return
    isLoadingProfissionais.value = true
    errorProfissionais.value = null
    try {
      let query = supabase
        .from('conversas')
        .select('id, numero, nome_contato, ultima_mensagem, ultimo_horario, created_at, instancia:instancias(profissional:profissionais(id, nome))')
        .is('deleted_at', null)
        .order('ultimo_horario', { ascending: false, nullsFirst: false })

      if (filtros?.data_inicio) {
        query = query.gte('created_at', new Date(filtros.data_inicio).toISOString())
      }
      if (filtros?.data_fim) {
        const fim = new Date(filtros.data_fim)
        fim.setHours(23, 59, 59, 999)
        query = query.lte('created_at', fim.toISOString())
      }

      const { data, error: err } = await query
      if (err) {
        errorProfissionais.value = `Erro ao carregar clientes: ${err.message}`
        return
      }

      let lista: ClienteViaProfissional[] = (data || []).map((c: any) => {
        const inst = Array.isArray(c.instancia) ? c.instancia[0] : c.instancia
        const profRaw = inst?.profissional
        const prof = Array.isArray(profRaw) ? profRaw[0] : profRaw
        return {
          id: c.id,
          nome: c.nome_contato || c.numero,
          telefone: c.numero,
          profissional_id: prof?.id || null,
          // Toda linha aqui SÓ existe porque em algum momento um profissional
          // vinculado recebeu mensagem nesse canal — se o embed vier vazio
          // agora, é porque o profissional foi excluído depois (nunca é "nunca
          // teve profissional"), daí o rótulo diferente do genérico.
          profissional_nome: prof?.nome || 'Profissional removido',
          ultima_mensagem: c.ultima_mensagem,
          created_at: c.ultimo_horario || c.created_at
        }
      })

      // O mesmo telefone pode aparecer em MAIS de uma instância — ex.: o
      // profissional que atendia foi excluído e outro assumiu esse cliente
      // depois (mensagem por um canal diferente = conversa diferente por
      // natureza, ver handoff §2.2). Sem isso o mesmo cliente aparecia
      // duplicado: uma vez "Profissional removido", outra com quem pegou o
      // cliente depois. A query já vem ordenada por ultimo_horario desc —
      // mantém só a conversa mais recente por telefone (quem fala com o
      // cliente AGORA é quem aparece na lista).
      const telefonesVistos = new Set<string>()
      lista = lista.filter((c) => {
        if (telefonesVistos.has(c.telefone)) return false
        telefonesVistos.add(c.telefone)
        return true
      })

      // Filtro por profissional é sobre o embed aninhado (instancia.profissional) —
      // mais simples filtrar aqui do que montar `!inner` no PostgREST via JS client.
      if (filtros?.profissional_id) {
        lista = lista.filter((c) => c.profissional_id === filtros.profissional_id)
      }

      clientesProfissionais.value = lista
    } catch {
      errorProfissionais.value = 'Erro inesperado ao carregar clientes'
    } finally {
      isLoadingProfissionais.value = false
    }
  }

  // Exclui a CONVERSA (soft delete, mesma rota usada na página Conversas) —
  // nunca mexe em `contatos`/`clientes`, são fontes independentes.
  const deleteClienteProfissional = async (conversaId: string): Promise<boolean> => {
    try {
      const headers = await (async () => {
        if (!supabase) return {}
        const { data } = await supabase.auth.getSession()
        return data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {}
      })()
      const res = await fetch(`/api/conversas/${conversaId}/excluir`, { method: 'POST', headers })
      if (!res.ok) throw new Error('Falha ao excluir')
      clientesProfissionais.value = clientesProfissionais.value.filter((c) => c.id !== conversaId)
      return true
    } catch (err: any) {
      errorProfissionais.value = `Erro ao excluir cliente: ${err?.message || err}`
      return false
    }
  }

  const clearErrorProfissionais = (): void => {
    errorProfissionais.value = null
  }

  return {
    clientes,
    isLoading,
    error,
    fetchClientes,
    deleteCliente,
    despausar,
    clearError,
    clientesProfissionais,
    isLoadingProfissionais,
    errorProfissionais,
    fetchClientesViaProfissionais,
    deleteClienteProfissional,
    clearErrorProfissionais
  }
}
