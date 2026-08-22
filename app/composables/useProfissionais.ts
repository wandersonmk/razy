import { ref } from 'vue'

export interface ProfissionalInstancia {
  id: string
  nome_instancia: string
  phone: string | null
  status: string
}

export interface Profissional {
  id: string
  usuario_id: string
  nome: string
  telefone: string | null
  avatar_url: string | null
  ativo: boolean
  created_at: string
  instancia: ProfissionalInstancia | null
  assistente_ia: { id: string; ativo: boolean }[] | { id: string; ativo: boolean } | null
}

async function authHeader(): Promise<Record<string, string>> {
  if (process.server) return {}
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token
    ? { Authorization: `Bearer ${data.session.access_token}` }
    : {}
}

export function useProfissionais() {
  const profissionais = ref<Profissional[]>([])
  const isLoading = ref(false)

  const fetchProfissionais = async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) isLoading.value = true
    try {
      const headers = await authHeader()
      const res = await fetch('/api/profissionais', { headers })
      if (res.ok) profissionais.value = (await res.json()) as Profissional[]
    } finally {
      if (!opts?.silent) isLoading.value = false
    }
  }

  const criarProfissional = async (nome: string, telefone?: string) => {
    const headers = await authHeader()
    const res = await fetch('/api/profissionais', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ nome, telefone })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data?.statusMessage || data?.message || 'Erro ao cadastrar profissional')
    return data as Profissional
  }

  // Cria o profissional e já gera a instância (canal) vinculada a ele — o fluxo
  // de "cadastrar profissional" da página nasce direto pronto pra gerar QR Code.
  const criarProfissionalComCanal = async (nome: string, telefone?: string) => {
    const profissional = await criarProfissional(nome, telefone)
    const headers = await authHeader()
    const res = await fetch('/api/instancias/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ nome_instancia: nome, profissional_id: profissional.id })
    })
    const instancia = await res.json()
    if (!res.ok) {
      throw new Error(instancia?.statusMessage || instancia?.message || 'Profissional criado, mas falhou ao gerar o canal')
    }
    return { profissional, instancia }
  }

  const atualizarProfissional = async (id: string, patch: Record<string, unknown>) => {
    const headers = await authHeader()
    const res = await fetch(`/api/profissionais/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify(patch)
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data?.statusMessage || data?.message || 'Erro ao salvar profissional')
    return data as Profissional
  }

  const excluirProfissional = async (id: string) => {
    const headers = await authHeader()
    const res = await fetch(`/api/profissionais/${id}`, { method: 'DELETE', headers })
    if (!res.ok) {
      const data = await res.json().catch(() => ({} as any))
      throw new Error(data?.statusMessage || data?.message || 'Erro ao excluir profissional')
    }
    profissionais.value = profissionais.value.filter((p) => p.id !== id)
  }

  return {
    profissionais,
    isLoading,
    fetchProfissionais,
    criarProfissional,
    criarProfissionalComCanal,
    atualizarProfissional,
    excluirProfissional
  }
}

// Aceita tanto o objeto quanto o array que o PostgREST pode devolver pro embed 1:1.
export function iaDoProfissionalAtiva(p: Profissional): boolean {
  const rel = p.assistente_ia
  if (!rel) return false
  const row = Array.isArray(rel) ? rel[0] : rel
  return !!row?.ativo
}
