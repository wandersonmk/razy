import { ref } from 'vue'

export interface ConversaInstancia {
  id: string
  nome_instancia: string
  phone: string | null
  status: string
  profissional_id: string | null
}

export interface ConversaProfissional {
  id: string
  nome: string
}

export interface Conversa {
  id: string
  numero: string
  nome_contato: string | null
  nome_editado: boolean
  photo: string | null
  ultima_mensagem: string | null
  ultimo_horario: string | null
  ultima_msg_cliente_em: string | null
  nao_lidas: number
  importante: boolean
  status: string
  instancia_id: string | null
  assigned_to_professional_id: string | null
  assigned_at: string | null
  opened_at: string | null
  closed_at: string | null
  resolved_at: string | null
  tempo_pausa: number | null
  tempo_pausa_inicio: string | null
  arquivada: boolean
  created_at: string
  updated_at: string
  instancia: ConversaInstancia | null
  profissional: ConversaProfissional | null
}

export interface MensagemMidia {
  id: string
  tipo: string
  storage_path: string
  url_storage: string
}

export interface Mensagem {
  id: string
  conversa_id: string
  numero: string
  nome_contato: string | null
  mensagem: string | null
  direcao: 'RECEIVED' | 'SENT'
  enviado_por: 'user' | 'assistant' | 'celular'
  enviado_por_profissional_id: string | null
  kind: string
  arquivo_nome: string | null
  wa_message_id: string | null
  reply_to_wa_id: string | null
  reply_to_text: string | null
  reply_to_from_me: boolean | null
  data_hora: string
  created_at: string
  midia: MensagemMidia[] | MensagemMidia | null
}

export type Aba = 'todas' | 'nao_atribuidas' | 'resolvidas' | 'arquivadas'

export interface HistoricoEvento {
  id: string
  conversa_id: string
  profissional_id: string | null
  profissional_nome_snapshot: string | null
  acao: 'atribuido' | 'desatribuido' | 'fechado'
  created_by: string | null
  created_at: string
}

async function authHeader(): Promise<Record<string, string>> {
  if (process.server) return {}
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token
    ? { Authorization: `Bearer ${data.session.access_token}` }
    : {}
}

// Normaliza o embed do PostgREST (1:1 pode vir objeto OU array de 1, conforme a
// versão do PostgREST/relação detectada) para sempre um objeto ou null.
function um<T>(v: T | T[] | null | undefined): T | null {
  if (!v) return null
  return Array.isArray(v) ? (v[0] ?? null) : v
}

function normalizarConversa(raw: any): Conversa {
  return { ...raw, instancia: um(raw.instancia), profissional: um(raw.profissional) }
}

function normalizarMensagem(raw: any): Mensagem {
  return { ...raw, midia: um(raw.midia) }
}

export function useConversas() {
  const conversas = ref<Conversa[]>([])
  const isLoading = ref(false)

  const fetchConversas = async (opts?: { aba?: Aba; instanciaId?: string | null; busca?: string; silent?: boolean }) => {
    if (!opts?.silent) isLoading.value = true
    try {
      const headers = await authHeader()
      const params = new URLSearchParams()
      params.set('aba', opts?.aba || 'todas')
      if (opts?.instanciaId) params.set('instancia_id', opts.instanciaId)
      if (opts?.busca) params.set('busca', opts.busca)
      const res = await fetch(`/api/conversas?${params.toString()}`, { headers })
      if (res.ok) {
        const data = (await res.json()) as any[]
        conversas.value = data.map(normalizarConversa)
      }
    } finally {
      if (!opts?.silent) isLoading.value = false
    }
  }

  const fetchMensagens = async (conversaId: string, opts?: { before?: string; limit?: number }): Promise<Mensagem[]> => {
    const headers = await authHeader()
    const params = new URLSearchParams()
    if (opts?.before) params.set('before', opts.before)
    if (opts?.limit) params.set('limit', String(opts.limit))
    const res = await fetch(`/api/conversas/${conversaId}/mensagens?${params.toString()}`, { headers })
    if (!res.ok) return []
    const data = (await res.json()) as any[]
    return data.map(normalizarMensagem)
  }

  async function acao(id: string, caminho: string, body?: Record<string, unknown>) {
    const headers = await authHeader()
    const res = await fetch(`/api/conversas/${id}/${caminho}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify(body || {})
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data?.statusMessage || data?.message || `Erro ao ${caminho}`)
    return normalizarConversa(data)
  }

  const abrirAtendimento = (id: string, profissionalId?: string | null) => acao(id, 'abrir', { profissional_id: profissionalId })
  const fecharAtendimento = (id: string) => acao(id, 'fechar')
  const atribuir = (id: string, profissionalId: string | null) => acao(id, 'atribuir', { profissional_id: profissionalId })
  const arquivar = (id: string, arquivada: boolean) => acao(id, 'arquivar', { arquivada })
  const pausar = (id: string, minutos: number) => acao(id, 'pausar', { minutos })
  const despausar = (id: string) => acao(id, 'despausar')
  const renomearContato = (id: string, nomeContato: string) => acao(id, 'nome', { nome_contato: nomeContato })

  const fetchHistorico = async (id: string): Promise<HistoricoEvento[]> => {
    const headers = await authHeader()
    const res = await fetch(`/api/conversas/${id}/historico`, { headers })
    if (!res.ok) return []
    return await res.json()
  }

  // Signed URL da mídia — o bucket é privado, a policy só libera leitura pro
  // dono (path começa com o próprio usuario_id). Expira em 1h.
  const urlAssinadaMidia = async (path: string): Promise<string | null> => {
    if (process.server) return null
    try {
      const supabase = useSupabaseClient()
      const { data, error } = await supabase.storage.from('conversas-midia').createSignedUrl(path, 3600)
      if (error) return null
      return data?.signedUrl || null
    } catch {
      return null
    }
  }

  return {
    conversas,
    isLoading,
    fetchConversas,
    fetchMensagens,
    abrirAtendimento,
    fecharAtendimento,
    atribuir,
    arquivar,
    pausar,
    despausar,
    renomearContato,
    fetchHistorico,
    urlAssinadaMidia,
    normalizarConversa,
    normalizarMensagem
  }
}

// Opções fixas do seletor de pausa manual (minutos).
export const OPCOES_PAUSA = [
  { label: '1 hora', minutos: 60 },
  { label: '24 horas', minutos: 60 * 24 },
  { label: '10 dias', minutos: 60 * 24 * 10 },
  { label: 'Permanente', minutos: 60 * 24 * 365 }
] as const

export const PAUSA_PERMANENTE_MINUTOS = 60 * 24 * 365
