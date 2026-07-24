import { ref } from 'vue'

export interface AssistenteInstancia {
  id: string
  nome_instancia: string
  phone: string | null
  status: string
}

export interface Assistente {
  id: string
  usuario_id: string
  instancia_id: string | null
  nome: string
  tipo: string
  ativo: boolean
  empresa_nome: string | null
  empresa_info: string | null
  horario_funcionamento: string | null
  instrucao: string | null
  atendente_telefone: string | null
  notificar_rotativo: boolean
  pausa_ativa: boolean
  pausa_minutos: number
  created_at: string
  updated_at: string
  instancia: AssistenteInstancia | null
}

async function authHeader(): Promise<Record<string, string>> {
  if (process.server) return {}
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token
    ? { Authorization: `Bearer ${data.session.access_token}` }
    : {}
}

export function useAssistentes() {
  const assistentes = ref<Assistente[]>([])
  const isLoading = ref(false)

  const fetchAssistentes = async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) isLoading.value = true
    try {
      const headers = await authHeader()
      const res = await fetch('/api/assistentes', { headers })
      if (res.ok) assistentes.value = (await res.json()) as Assistente[]
    } finally {
      if (!opts?.silent) isLoading.value = false
    }
  }

  const criarAssistente = async (payload: { nome: string; tipo?: string; instancia_id?: string | null }) => {
    const headers = await authHeader()
    const res = await fetch('/api/assistentes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data?.statusMessage || data?.message || 'Erro ao criar assistente')
    return data as Assistente
  }

  const atualizarAssistente = async (id: string, patch: Record<string, unknown>) => {
    const headers = await authHeader()
    const res = await fetch(`/api/assistentes/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify(patch)
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data?.statusMessage || data?.message || 'Erro ao salvar assistente')
    return data as Assistente
  }

  const excluirAssistente = async (id: string) => {
    const headers = await authHeader()
    const res = await fetch(`/api/assistentes/${id}`, { method: 'DELETE', headers })
    if (!res.ok) {
      const data = await res.json().catch(() => ({} as any))
      throw new Error(data?.statusMessage || data?.message || 'Erro ao excluir assistente')
    }
    assistentes.value = assistentes.value.filter((a) => a.id !== id)
  }

  return { assistentes, isLoading, fetchAssistentes, criarAssistente, atualizarAssistente, excluirAssistente }
}

// ── Metadados de tipo (rótulo + cor do headset do robô) ──────────────────────
export const TIPOS_ASSISTENTE = [
  { id: 'principal', label: 'Principal', cor: '#7c3aed' },
  { id: 'comercial', label: 'Comercial', cor: '#2563eb' },
  { id: 'financeiro', label: 'Financeiro', cor: '#f59e0b' },
  { id: 'suporte', label: 'Suporte', cor: '#0ea5e9' },
  { id: 'pos_venda', label: 'Pós-venda', cor: '#10b981' },
  { id: 'outro', label: 'Outro', cor: '#64748b' }
] as const

export function tipoMeta(tipo: string) {
  return TIPOS_ASSISTENTE.find((t) => t.id === tipo) || TIPOS_ASSISTENTE[TIPOS_ASSISTENTE.length - 1]
}
