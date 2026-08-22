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

// 1 linha por CONVERSA (cliente) atendida no período — o "quem o profissional
// atendeu", não só o agregado por profissional.
export interface AtendimentoDetalhado {
  conversa_id: string
  profissional_id: string | null
  profissional_nome: string | null
  cliente_nome: string | null
  cliente_numero: string
  mensagens_recebidas: number
  mensagens_enviadas: number
  primeira_recebida_em: string | null
  primeira_resposta_em: string | null
  tmpr_seg: number | null
}

export function useRelatorioAtendimento() {
  const metricas = ref<MetricaProfissional[]>([])
  const diario = ref<MetricaDiaria[]>([])
  const detalhes = ref<AtendimentoDetalhado[]>([])
  const isLoading = ref(false)
  const isLoadingDiario = ref(false)
  const isLoadingDetalhes = ref(false)

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

  const fetchDetalhes = async (dias = 30) => {
    isLoadingDetalhes.value = true
    try {
      const headers = await authHeader()
      const res = await fetch(`/api/relatorios/atendimento-detalhado?dias=${dias}`, { headers })
      if (res.ok) detalhes.value = (await res.json()) as AtendimentoDetalhado[]
    } finally {
      isLoadingDetalhes.value = false
    }
  }

  return {
    metricas, diario, detalhes,
    isLoading, isLoadingDiario, isLoadingDetalhes,
    fetchMetricas, fetchDiario, fetchDetalhes
  }
}

// Mesmo padrão usado em ChatConversa.vue / ProfissionaisManager.vue.
export function formatarTelefone(tel: string | null | undefined): string {
  if (!tel) return '—'
  const n = tel.replace(/\D/g, '')
  if (n.length === 13) return `+${n.slice(0, 2)} ${n.slice(2, 4)} ${n.slice(4, 9)}-${n.slice(9)}`
  if (n.length === 12) return `+${n.slice(0, 2)} ${n.slice(2, 4)} ${n.slice(4, 8)}-${n.slice(8)}`
  return tel
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
