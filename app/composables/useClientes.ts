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
}

export interface FiltrosClientes {
  campanha_id?: string
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
    } catch (err: any) {
      error.value = 'Erro inesperado ao carregar clientes'
    } finally {
      isLoading.value = false
    }
  }

  // "Clientes" é uma visão derivada — não há tabela própria para deletar.
  // Remove apenas da lista local (some da sessão atual).
  const deleteCliente = async (clienteId: string): Promise<boolean> => {
    clientes.value = clientes.value.filter((c) => c.id !== clienteId)
    return true
  }

  const clearError = (): void => {
    error.value = null
  }

  return {
    clientes,
    isLoading,
    error,
    fetchClientes,
    deleteCliente,
    clearError
  }
}
