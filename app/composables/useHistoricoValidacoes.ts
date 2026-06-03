// Histórico das validações de números (persistido no Supabase, RLS por usuário).
// Guarda metadados + os dados necessários para regenerar os dois arquivos depois.
import { ref } from 'vue'

export interface ItemHistorico {
  id: string
  nome_arquivo: string
  canal: string
  total: number
  validos_count: number
  invalidos_count: number
  created_at: string
}

export function useHistoricoValidacoes() {
  let supabase: any = null
  if (typeof window !== 'undefined') supabase = useSupabaseClient()

  const itens = ref<ItemHistorico[]>([])
  const isLoading = ref(false)

  async function listar() {
    if (!supabase) return
    isLoading.value = true
    try {
      const { data, error } = await supabase
        .from('validacoes_numeros')
        .select('id, nome_arquivo, canal, total, validos_count, invalidos_count, created_at')
        .order('created_at', { ascending: false })
        .limit(100)
      if (!error) itens.value = data || []
    } finally {
      isLoading.value = false
    }
  }

  // snapshot vem de useValidadorNumeros().snapshotHistorico()
  async function salvar(snapshot: any): Promise<boolean> {
    if (!supabase || !snapshot) return false
    const { data: u } = await supabase.auth.getUser()
    const usuario_id = u?.user?.id
    if (!usuario_id) return false
    const { error } = await supabase.from('validacoes_numeros').insert({ ...snapshot, usuario_id })
    if (error) return false
    await listar()
    return true
  }

  async function excluir(id: string) {
    if (!supabase) return
    const { error } = await supabase.from('validacoes_numeros').delete().eq('id', id)
    if (!error) itens.value = itens.value.filter((i) => i.id !== id)
  }

  async function baixar(id: string, tipo: 'validos' | 'invalidos') {
    if (!supabase) return
    const { data, error } = await supabase
      .from('validacoes_numeros')
      .select('nome_arquivo, dados')
      .eq('id', id)
      .single()
    if (error || !data) return
    const dados = data.dados || {}
    const linhas = tipo === 'validos' ? (dados.validos || []) : (dados.invalidos || [])
    if (!linhas.length) return
    const XLSX = await import('xlsx')
    const aoa = [dados.headers || [], ...linhas]
    const ws = XLSX.utils.aoa_to_sheet(aoa)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, tipo === 'validos' ? 'Validos' : 'Sem WhatsApp')
    XLSX.writeFile(wb, `${data.nome_arquivo || 'contatos'}-${tipo}.xlsx`)
  }

  return { itens, isLoading, listar, salvar, excluir, baixar }
}
