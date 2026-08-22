import { ref } from 'vue'

export interface MetricaProfissional {
  profissional_id: string
  profissional_nome: string
  mensagens_recebidas: number
  mensagens_enviadas: number
  atendimentos: number
  tmpr_seg: number | null
}

async function authHeader(): Promise<Record<string, string>> {
  if (process.server) return {}
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token
    ? { Authorization: `Bearer ${data.session.access_token}` }
    : {}
}

export interface MetricaDiaria {
  dia: string
  mensagens_recebidas: number
  mensagens_enviadas: number
  atendimentos: number
  tmpr_medio_seg: number | null
}

export function useRelatorioAtendimento() {
  const metricas = ref<MetricaProfissional[]>([])
  const diario = ref<MetricaDiaria[]>([])
  const isLoading = ref(false)
  const isLoadingDiario = ref(false)

  const fetchMetricas = async (dias = 30) => {
    isLoading.value = true
    try {
      const headers = await authHeader()
      const res = await fetch(`/api/relatorios/atendimento?dias=${dias}`, { headers })
      if (res.ok) metricas.value = (await res.json()) as MetricaProfissional[]
    } finally {
      isLoading.value = false
    }
  }

  const fetchDiario = async (dias = 30) => {
    isLoadingDiario.value = true
    try {
      const headers = await authHeader()
      const res = await fetch(`/api/relatorios/atendimento-diario?dias=${dias}`, { headers })
      if (res.ok) diario.value = (await res.json()) as MetricaDiaria[]
    } finally {
      isLoadingDiario.value = false
    }
  }

  return { metricas, diario, isLoading, isLoadingDiario, fetchMetricas, fetchDiario }
}

export function formatarDuracaoSegundos(seg: number | null): string {
  if (seg === null || seg === undefined || Number.isNaN(seg)) return '—'
  const total = Math.round(seg)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}
