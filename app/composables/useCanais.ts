import { ref } from 'vue'

export interface Canal {
  id: string
  usuario_id: string
  nome: string
  tipo: 'nativo' | 'oficial_meta' | 'instagram'
  instancia_id: string | null
  instancia_token: string | null
  telefone: string | null
  status: 'desconectado' | 'aguardando_qr' | 'conectando' | 'conectado' | 'erro'
  created_at: string
  updated_at: string
}

type BackendInstancia = {
  id: string
  usuario_id: string
  nome_instancia: string
  uazapi_instance_name: string | null
  uazapi_token: string | null
  phone: string | null
  status: string
  created_at?: string
  updated_at?: string
}

const STATUS_BACK_TO_FRONT: Record<string, Canal['status']> = {
  connected: 'conectado',
  qr: 'aguardando_qr',
  connecting: 'conectando',
  disconnected: 'desconectado',
  error: 'erro'
}

function mapInstancia(i: BackendInstancia): Canal {
  return {
    id: i.id,
    usuario_id: i.usuario_id,
    nome: i.nome_instancia,
    tipo: 'nativo',
    instancia_id: i.uazapi_instance_name,
    instancia_token: i.uazapi_token,
    telefone: i.phone,
    status: STATUS_BACK_TO_FRONT[i.status] ?? 'desconectado',
    created_at: i.created_at ?? '',
    updated_at: i.updated_at ?? ''
  }
}

function mapStatus(raw: string | undefined | null): Canal['status'] {
  return STATUS_BACK_TO_FRONT[String(raw ?? '').toLowerCase()] ?? 'desconectado'
}

async function authHeader(): Promise<Record<string, string>> {
  if (process.server) return {}
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token
    ? { Authorization: `Bearer ${data.session.access_token}` }
    : {}
}

export function useCanais() {
  const canais = ref<Canal[]>([])
  const isLoading = ref(false)

  const fetchCanais = async () => {
    isLoading.value = true
    try {
      const headers = await authHeader()
      const res = await fetch('/api/instancias', { headers })
      if (res.ok) {
        const data: BackendInstancia[] = await res.json()
        canais.value = data.map(mapInstancia)
      }
    } finally {
      isLoading.value = false
    }
  }

  const criarCanal = async (nome: string, _tipo: Canal['tipo'] = 'nativo') => {
    const headers = await authHeader()
    const res = await fetch('/api/instancias/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ nome_instancia: nome })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data?.statusMessage || data?.message || 'Erro ao criar canal')
    return mapInstancia(data as BackendInstancia)
  }

  const conectar = async (id: string): Promise<{ qrcode: string | null; paircode?: string; connected: boolean; status: Canal['status']; erro?: string }> => {
    const headers = await authHeader()
    const res = await fetch(`/api/instancias/${id}/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ systemName: 'Razy' })
    })
    const data = await res.json()
    if (!res.ok) return { qrcode: null, connected: false, status: 'erro', erro: data?.statusMessage || data?.message || `HTTP ${res.status}` }
    return {
      qrcode: data?.qrcode ?? null,
      paircode: data?.paircode ?? undefined,
      connected: !!data?.connected,
      status: mapStatus(data?.status)
    }
  }

  const buscarStatus = async (id: string): Promise<{ status: Canal['status']; telefone?: string }> => {
    const headers = await authHeader()
    const res = await fetch(`/api/instancias/${id}/status`, { headers })
    const data = await res.json()
    return { status: mapStatus(data?.status), telefone: data?.phone ?? undefined }
  }

  const renomear = async (id: string, nome: string) => {
    const headers = await authHeader()
    const res = await fetch(`/api/instancias/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ nome_instancia: nome })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data?.statusMessage || data?.message || 'Erro ao renomear canal')
    const atualizada = mapInstancia(data as BackendInstancia)
    canais.value = canais.value.map((c) => (c.id === id ? atualizada : c))
    return atualizada
  }

  const desconectar = async (id: string) => {
    const headers = await authHeader()
    await fetch(`/api/instancias/${id}/disconnect`, { method: 'POST', headers })
    await fetchCanais()
  }

  const excluir = async (id: string) => {
    const headers = await authHeader()
    await fetch(`/api/instancias/${id}`, { method: 'DELETE', headers })
    canais.value = canais.value.filter((c) => c.id !== id)
  }

  return { canais, isLoading, fetchCanais, criarCanal, conectar, buscarStatus, renomear, desconectar, excluir }
}
