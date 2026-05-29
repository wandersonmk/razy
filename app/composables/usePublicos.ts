import { ref } from 'vue'
import type { SupabaseClient } from '@supabase/supabase-js'

export interface Publico {
  id: string
  usuario_id: string
  nome: string
  regiao: string | null
  status: 'frio' | 'morno' | 'quente'
  created_at: string
  total_contatos?: number
}

export function usePublicos() {
  const publicos = ref<Publico[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const getSupabase = (): SupabaseClient | null => {
    if (process.server) return null
    return useSupabaseClient()
  }

  const fetchPublicos = async () => {
    const supabase = getSupabase()
    if (!supabase) return

    isLoading.value = true
    error.value = null
    try {
      const { data, error: err } = await supabase
        .from('publicos')
        .select('*')
        .order('created_at', { ascending: false })

      if (err) throw err

      // Buscar contagem de contatos para cada público
      const publicosComContagem = await Promise.all(
        (data || []).map(async (pub) => {
          const { count } = await supabase
            .from('contatos')
            .select('*', { count: 'exact', head: true })
            .eq('publico_id', pub.id)
          return { ...pub, total_contatos: count ?? 0 }
        })
      )

      publicos.value = publicosComContagem
    } catch (err: any) {
      error.value = err.message
    } finally {
      isLoading.value = false
    }
  }

  const criarPublico = async (payload: { nome: string; regiao?: string; status: 'frio' | 'morno' | 'quente' }) => {
    const supabase = getSupabase()
    if (!supabase) return null

    const { data: userData } = await supabase.auth.getUser()
    if (!userData.user) return null

    const { data, error: err } = await supabase
      .from('publicos')
      .insert({ ...payload, usuario_id: userData.user.id })
      .select()
      .single()

    if (err) throw err
    return data
  }

  const excluirPublico = async (id: string) => {
    const supabase = getSupabase()
    if (!supabase) return

    const { error: err } = await supabase
      .from('publicos')
      .delete()
      .eq('id', id)

    if (err) throw err
    publicos.value = publicos.value.filter((p) => p.id !== id)
  }

  return { publicos, isLoading, error, fetchPublicos, criarPublico, excluirPublico }
}
