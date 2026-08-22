export interface AssistenteProfissional {
  id: string
  usuario_id: string
  profissional_id: string
  ativo: boolean
  empresa_nome: string | null
  empresa_info: string | null
  horario_funcionamento: string | null
  instrucao: string | null
  ler_imagem: boolean
  instrucao_imagem: string | null
  ler_documento: boolean
  instrucao_documento: string | null
  pausa_ativa: boolean
  pausa_minutos: number
  created_at: string
  updated_at: string
}

async function authHeader(): Promise<Record<string, string>> {
  if (process.server) return {}
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token
    ? { Authorization: `Bearer ${data.session.access_token}` }
    : {}
}

// IA por profissional: modelo separado do assistente atual (useAssistentes.ts).
// Nunca compartilha tabela nem endpoint com ele.
export function useAssistentesProfissionais() {
  const buscarPorProfissional = async (profissionalId: string): Promise<AssistenteProfissional | null> => {
    const headers = await authHeader()
    const res = await fetch(`/api/profissionais/${profissionalId}/assistente`, { headers })
    if (!res.ok) return null
    return await res.json()
  }

  const salvar = async (profissionalId: string, patch: Record<string, unknown>) => {
    const headers = await authHeader()
    const res = await fetch(`/api/profissionais/${profissionalId}/assistente`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify(patch)
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data?.statusMessage || data?.message || 'Erro ao salvar a IA do profissional')
    return data as AssistenteProfissional
  }

  return { buscarPorProfissional, salvar }
}
