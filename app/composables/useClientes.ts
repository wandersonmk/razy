// "Clientes" = contatos que RESPONDERAM a algum disparo (registrado via webhook).
// A fonte é a tabela `disparos` (respondido_em não nulo) + join no contato.

export interface Cliente {
  id: string
  nome: string
  telefone: string
  empresa?: string
  created_at: string          // aqui = data da resposta (respondido_em)
  resposta_texto?: string | null
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
  const fetchClientes = async (): Promise<void> => {
    if (!supabase) return
    isLoading.value = true
    error.value = null
    try {
      const { data, error: err } = await supabase
        .from('disparos')
        .select('contato_id, resposta_texto, respondido_em, contato:contatos(id, nome, telefone, empresa)')
        .not('respondido_em', 'is', null)
        .order('respondido_em', { ascending: false })

      if (err) {
        error.value = `Erro ao carregar clientes: ${err.message}`
        return
      }

      // Deduplica por contato, mantendo a resposta mais recente (já vem ordenado desc).
      const vistos = new Set<string>()
      const lista: Cliente[] = []
      for (const d of data || []) {
        const c = (d as any).contato
        if (!c || vistos.has(c.id)) continue
        vistos.add(c.id)
        lista.push({
          id: c.id,
          nome: c.nome || '—',
          telefone: c.telefone,
          empresa: c.empresa || '',
          created_at: (d as any).respondido_em,
          resposta_texto: (d as any).resposta_texto
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
