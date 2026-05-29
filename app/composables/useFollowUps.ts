export interface FollowUpEtapa {
  id?: string
  config_id?: string
  ordem: number
  delay_minutos: number
  modo_mensagem: 'ia' | 'manual'
  mensagem?: string | null
}

export interface FollowUpConfig {
  id: string
  campanha_id: string
  ativo: boolean
  criado_em: string
  campanha?: { id: string; nome: string; status: string; total_enviados: number }
  etapas: FollowUpEtapa[]
  metricas?: {
    total: number; enviados: number; responderam: number; pendentes: number; cancelados: number
  }
}

export function useFollowUps() {
  const configs = ref<FollowUpConfig[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function authHeaders(): Promise<Record<string, string>> {
    if (process.server) return {}
    const sb = useSupabaseClient()
    const { data } = await sb.auth.getSession()
    return data.session?.access_token
      ? { Authorization: `Bearer ${data.session.access_token}` }
      : {}
  }

  const fetchConfigs = async () => {
    isLoading.value = true
    error.value = null
    try {
      const headers = await authHeaders()
      const data = await $fetch<FollowUpConfig[]>('/api/followups', { headers })
      configs.value = data || []
    } catch (e: any) {
      error.value = e.message || 'Erro ao carregar follow-ups'
    } finally {
      isLoading.value = false
    }
  }

  const fetchMetricas = async (id: string) => {
    try {
      const headers = await authHeaders()
      const m = await $fetch<any>(`/api/followups/${id}/metricas`, { headers })
      const idx = configs.value.findIndex(c => c.id === id)
      if (idx !== -1) configs.value[idx].metricas = m
      return m
    } catch { return null }
  }

  const criar = async (payload: { campanha_id: string; etapas: FollowUpEtapa[] }) => {
    const headers = await authHeaders()
    const data = await $fetch<FollowUpConfig>('/api/followups', {
      method: 'POST', headers,
      body: payload
    })
    await fetchConfigs()
    return data
  }

  const remover = async (id: string) => {
    const headers = await authHeaders()
    await $fetch(`/api/followups/${id}`, { method: 'DELETE', headers })
    configs.value = configs.value.filter(c => c.id !== id)
  }

  const toggleAtivo = async (id: string, ativo: boolean) => {
    const headers = await authHeaders()
    await $fetch(`/api/followups/${id}/toggle`, { method: 'PATCH', headers, body: { ativo } })
    const idx = configs.value.findIndex(c => c.id === id)
    if (idx !== -1) configs.value[idx].ativo = ativo
  }

  return { configs, isLoading, error, fetchConfigs, fetchMetricas, criar, remover, toggleAtivo }
}
