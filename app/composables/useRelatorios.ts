// Relatórios = histórico de disparos (com contato, campanha, status e resposta).
export interface DisparoRelatorio {
  id: string
  campanha_id: string
  campanha_nome: string
  contato_nome: string
  telefone: string
  canal_id: string | null
  canal_telefone: string
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
          'id, campanha_id, canal_id, status, mensagem_enviada, resposta_texto, respondido_em, enviado_em, created_at, ' +
          'contato:contatos(nome, telefone), campanha:campanhas(nome)'
        )
        .order('created_at', { ascending: false })
        .limit(1000)

      if (err) throw err

      // Mapa canal_id -> número que enviou. Sem FK disparos→instancias, então
      // buscamos as instâncias do usuário (RLS escopa por usuario_id) e cruzamos aqui.
      const { data: inst } = await supabase
        .from('instancias')
        .select('id, phone, uazapi_instance_name')
      const canalPorId = new Map<string, string>()
      for (const i of inst || []) {
        canalPorId.set(i.id, i.phone || i.uazapi_instance_name || '—')
      }

      relatorios.value = (data || []).map((d: any) => ({
        id: d.id,
        campanha_id: d.campanha_id,
        campanha_nome: d.campanha?.nome || '—',
        contato_nome: d.contato?.nome || '—',
        telefone: d.contato?.telefone || '',
        canal_id: d.canal_id || null,
        canal_telefone: d.canal_id ? (canalPorId.get(d.canal_id) || '—') : '—',
        status: d.status,
        mensagem_enviada: d.mensagem_enviada,
        resposta_texto: d.resposta_texto,
        respondido_em: d.respondido_em,
        enviado_em: d.enviado_em,
        created_at: d.created_at
      }))

      // Enviados/falhas: somados das campanhas (precisos mesmo com o limite acima).
      const { data: camp } = await supabase
        .from('campanhas')
        .select('total_enviados, total_falhas')

      const enviados = (camp || []).reduce((s: number, c: any) => s + (c.total_enviados || 0), 0)
      const falhas = (camp || []).reduce((s: number, c: any) => s + (c.total_falhas || 0), 0)

      // Respostas: contagem de disparos efetivamente respondidos (1 por contato),
      // consistente com o que a tabela exibe — não conta mensagens repetidas.
      const { count: respostas } = await supabase
        .from('disparos')
        .select('id', { count: 'exact', head: true })
        .not('respondido_em', 'is', null)

      metricas.value = { total: enviados + falhas, enviados, falhas, respostas: respostas || 0 }
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
