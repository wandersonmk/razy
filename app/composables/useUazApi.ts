// Cliente para o proxy do servidor (/api/whatsapp/*).
// O token UAzAPI fica APENAS no .env do servidor — nunca chega ao navegador.

export interface EnvioResultado {
  telefone: string
  sucesso: boolean
  erro?: string
  resposta?: any
}

async function getAuthHeader(): Promise<Record<string, string>> {
  if (process.server) return {}
  const supabase = useSupabaseClient()
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function useUazApi() {
  const enviarMensagem = async (telefone: string, mensagem: string, canalId?: string): Promise<EnvioResultado> => {
    try {
      const auth = await getAuthHeader()
      const response = await fetch('/api/whatsapp/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...auth
        },
        body: JSON.stringify({ number: telefone, text: mensagem, canal_id: canalId })
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        return { telefone, sucesso: false, erro: data?.statusMessage || data?.message || `HTTP ${response.status}` }
      }

      return data
    } catch (err: any) {
      return { telefone, sucesso: false, erro: err.message || 'Erro de rede' }
    }
  }

  const verificarConexao = async (): Promise<{ ok: boolean; status?: string; erro?: string }> => {
    try {
      const auth = await getAuthHeader()
      const response = await fetch('/api/whatsapp/status', { headers: auth })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) return { ok: false, erro: data?.statusMessage || `HTTP ${response.status}` }
      return data
    } catch (err: any) {
      return { ok: false, erro: err.message || 'Erro de rede' }
    }
  }

  // Interpola variáveis na mensagem: {nome}, {telefone}, {empresa}, {observacao}, {etapa}
  const interpolarMensagem = (template: string, contato: Record<string, any>): string => {
    return template.replace(/\{(\w+)\}/g, (_, key) => {
      const value = contato[key] ?? contato[key.toLowerCase()]
      return value != null ? String(value) : ''
    })
  }

  return { enviarMensagem, verificarConexao, interpolarMensagem }
}
