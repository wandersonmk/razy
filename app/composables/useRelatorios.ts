// Relatórios = histórico de disparos (com contato, campanha, status e resposta).
export interface DisparoRelatorio {
  id: string
  campanha_id: string
  campanha_nome: string
  contato_nome: string
  telefone: string
  status: 'pendente' | 'enviado' | 'falhou'
  mensagem_enviada: string | null
  resposta_texto: string | null
  respondido_em: string | null
  enviado_em: string | null
  created_at: string
}

export interface MetricasRelatorio {
  total: number
  enviados: number
  falhas: number
  respostas: number
}

export const useRelatorios = () => {
  let supabase: any = null
  if (typeof window !== 'undefined') {
    supabase = useSupabaseClient()
  }

  const relatorios = ref<DisparoRelatorio[]>([])
  const metricas = ref<MetricasRelatorio>({ total: 0, enviados: 0, falhas: 0, respostas: 0 })
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const fetchRelatorios = async () => {
    if (!supabase) return
    isLoading.value = true
    error.value = null
    try {
      const { data, error: err } = await supabase
        .from('disparos')
        .select(
          'id, campanha_id, status, mensagem_enviada, resposta_texto, respondido_em, enviado_em, created_at, ' +
          'contato:contatos(nome, telefone), campanha:campanhas(nome)'
        )
        .order('created_at', { ascending: false })
        .limit(1000)

      if (err) throw err

      relatorios.value = (data || []).map((d: any) => ({
        id: d.id,
        campanha_id: d.campanha_id,
        campanha_nome: d.campanha?.nome || '—',
        contato_nome: d.contato?.nome || '—',
        telefone: d.contato?.telefone || '',
        status: d.status,
        mensagem_enviada: d.mensagem_enviada,
        resposta_texto: d.resposta_texto,
        respondido_em: d.respondido_em,
        enviado_em: d.enviado_em,
        created_at: d.created_at
      }))

      // Métricas totais (somadas das campanhas — precisas mesmo com o limite acima).
      const { data: camp } = await supabase
        .from('campanhas')
        .select('total_enviados, total_falhas, total_respostas')

      const enviados = (camp || []).reduce((s: number, c: any) => s + (c.total_enviados || 0), 0)
      const falhas = (camp || []).reduce((s: number, c: any) => s + (c.total_falhas || 0), 0)
      const respostas = (camp || []).reduce((s: number, c: any) => s + (c.total_respostas || 0), 0)
      metricas.value = { total: enviados + falhas, enviados, falhas, respostas }
    } catch (err: any) {
      error.value = err.message || 'Erro ao carregar relatórios'
      relatorios.value = []
    } finally {
      isLoading.value = false
    }
  }

  const clearError = () => { error.value = null }

  return { relatorios, metricas, isLoading, error, fetchRelatorios, clearError }
}
