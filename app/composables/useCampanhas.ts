import { ref } from 'vue'
import type { SupabaseClient } from '@supabase/supabase-js'

export interface Campanha {
  id: string
  usuario_id: string
  publico_id: string
  canal_id: string | null
  nome: string
  mensagem: string | null
  modo_mensagem: 'manual' | 'ia'
  intervalo_segundos: number
  agendado_para: string | null
  usar_roteamento: boolean
  alternar_canais: boolean
  status: 'rascunho' | 'em_andamento' | 'concluida' | 'pausada' | 'falhou'
  total_enviados: number
  total_falhas: number
  total_respostas: number
  instancia_token: string | null
  instancia_url: string | null
  created_at: string
  iniciado_em: string | null
  concluido_em: string | null
  publico?: { nome: string; total_contatos?: number }
  canal?: { nome: string; telefone?: string | null }
}

export function useCampanhas() {
  const campanhas = ref<Campanha[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const getSupabase = (): SupabaseClient | null => {
    if (process.server) return null
    return useSupabaseClient()
  }

  const fetchCampanhas = async (opts?: { silent?: boolean }) => {
    const supabase = getSupabase()
    if (!supabase) return

    if (!opts?.silent) isLoading.value = true
    error.value = null
    try {
      const { data, error: err } = await supabase
        .from('campanhas')
        .select('*, publico:publicos(nome)')
        .order('created_at', { ascending: false })

      if (err) throw err
      const lista = data || []
      // Respostas reais = contatos distintos que responderam (1 por cliente),
      // em vez do contador denormalizado total_respostas (que pode dessincronizar).
      const mapaRespostas = await contarRespostasPorCampanha(supabase, lista.map((c: any) => c.id))
      campanhas.value = lista.map((c: any) => ({ ...c, total_respostas: mapaRespostas.get(c.id) ?? 0 }))
    } catch (err: any) {
      error.value = err.message
    } finally {
      if (!opts?.silent) isLoading.value = false
    }
  }

  const criarCampanha = async (payload: {
    nome: string
    publico_id: string
    canal_id?: string
    mensagem?: string | null
    modo_mensagem?: 'manual' | 'ia'
    intervalo_segundos?: number
    agendado_para?: string | null
    usar_roteamento?: boolean
    alternar_canais?: boolean
    instancia_token?: string
    instancia_url?: string
  }) => {
    const supabase = getSupabase()
    if (!supabase) return null

    const { data: userData } = await supabase.auth.getUser()
    if (!userData.user) return null

    const { data, error: err } = await supabase
      .from('campanhas')
      .insert({ ...payload, usuario_id: userData.user.id })
      .select()
      .single()

    if (err) throw err
    return data
  }

  const atualizarStatus = async (id: string, status: Campanha['status']) => {
    const supabase = getSupabase()
    if (!supabase) return

    const updates: Partial<Campanha> = { status }
    if (status === 'em_andamento') updates.iniciado_em = new Date().toISOString()
    if (status === 'concluida' || status === 'falhou') updates.concluido_em = new Date().toISOString()

    const { error: err } = await supabase.from('campanhas').update(updates).eq('id', id)
    if (err) throw err

    const idx = campanhas.value.findIndex((c) => c.id === id)
    if (idx !== -1) Object.assign(campanhas.value[idx], updates)
  }

  const incrementarEnviados = async (campanha_id: string, enviados: number, falhas: number) => {
    const supabase = getSupabase()
    if (!supabase) return

    const campanha = campanhas.value.find((c) => c.id === campanha_id)
    if (!campanha) return

    await supabase
      .from('campanhas')
      .update({
        total_enviados: campanha.total_enviados + enviados,
        total_falhas: campanha.total_falhas + falhas
      })
      .eq('id', campanha_id)
  }

  const excluirCampanha = async (id: string) => {
    const supabase = getSupabase()
    if (!supabase) return

    const { error: err } = await supabase.from('campanhas').delete().eq('id', id)
    if (err) throw err
    campanhas.value = campanhas.value.filter((c) => c.id !== id)
  }

  const fetchMetricasTotais = async () => {
    const supabase = getSupabase()
    if (!supabase) return { total_enviados: 0, total_falhas: 0, total_campanhas: 0 }

    const { data } = await supabase
      .from('campanhas')
      .select('total_enviados, total_falhas, status')

    if (!data) return { total_enviados: 0, total_falhas: 0, total_campanhas: 0 }

    return {
      total_enviados: data.reduce((s, c) => s + (c.total_enviados || 0), 0),
      total_falhas: data.reduce((s, c) => s + (c.total_falhas || 0), 0),
      total_campanhas: data.length
    }
  }

  return {
    campanhas,
    isLoading,
    error,
    fetchCampanhas,
    criarCampanha,
    atualizarStatus,
    incrementarEnviados,
    excluirCampanha,
    fetchMetricasTotais
  }
}
