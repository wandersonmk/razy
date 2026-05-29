import { ref } from 'vue'
import type { SupabaseClient } from '@supabase/supabase-js'

export interface Contato {
  id: string
  publico_id: string
  usuario_id: string
  nome: string | null
  telefone: string
  email: string | null
  empresa: string | null
  etapa: string | null
  observacao: string | null
  dados_extras: Record<string, any> | null
  created_at: string
}

// Mapeia colunas do Excel para campos do sistema
function mapearLinha(row: Record<string, any>): Partial<Contato> {
  const get = (keys: string[]) => {
    for (const k of keys) {
      const found = Object.keys(row).find(
        (rk) => rk.toLowerCase().replace(/[\s.]/g, '') === k.toLowerCase().replace(/[\s.]/g, '')
      )
      if (found && row[found] !== undefined && row[found] !== null && String(row[found]).trim() !== '') {
        return String(row[found]).trim()
      }
    }
    return null
  }

  const rawPhone = get(['contatotelefones', 'telefone', 'phone', 'celular', 'whatsapp', 'fone'])
  const telefone = rawPhone ? rawPhone.replace(/\D/g, '') : null

  return {
    nome:      get(['contatonome', 'nome', 'name', 'cliente']),
    telefone:  telefone || '',
    email:     get(['contatoemail', 'email', 'e-mail']),
    empresa:   get(['empresa', 'produtoNome', 'nomeloja', 'loja']),
    etapa:     get(['etapa', 'status', 'stage']),
    observacao: get(['observacao', 'observação', 'obs', 'anotacao', 'anotação', 'historico', 'histórico'])
  }
}

export function useContatos() {
  const contatos = ref<Contato[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const getSupabase = (): SupabaseClient | null => {
    if (process.server) return null
    return useSupabaseClient()
  }

  const fetchContatos = async (publicoId: string) => {
    const supabase = getSupabase()
    if (!supabase) return

    isLoading.value = true
    error.value = null
    try {
      const { data, error: err } = await supabase
        .from('contatos')
        .select('*')
        .eq('publico_id', publicoId)
        .order('created_at', { ascending: false })

      if (err) throw err
      contatos.value = data || []
    } catch (err: any) {
      error.value = err.message
    } finally {
      isLoading.value = false
    }
  }

  const importarPlanilha = async (publicoId: string, rows: Record<string, any>[]) => {
    const supabase = getSupabase()
    if (!supabase) return { importados: 0, erros: 0 }

    const { data: userData } = await supabase.auth.getUser()
    if (!userData.user) return { importados: 0, erros: 0 }

    const registros = rows
      .map((row) => mapearLinha(row))
      .filter((c) => c.telefone && c.telefone.length >= 8)
      .map((c) => ({
        ...c,
        publico_id: publicoId,
        usuario_id: userData.user!.id
      }))

    if (registros.length === 0) return { importados: 0, erros: rows.length }

    // Inserir em lotes de 500
    let importados = 0
    const lote = 500
    for (let i = 0; i < registros.length; i += lote) {
      const { error: err } = await supabase
        .from('contatos')
        .insert(registros.slice(i, i + lote))
      if (!err) importados += Math.min(lote, registros.length - i)
    }

    return { importados, erros: rows.length - importados }
  }

  const adicionarContato = async (publicoId: string, contato: Omit<Contato, 'id' | 'usuario_id' | 'publico_id' | 'created_at'>) => {
    const supabase = getSupabase()
    if (!supabase) return null

    const { data: userData } = await supabase.auth.getUser()
    if (!userData.user) return null

    const { data, error: err } = await supabase
      .from('contatos')
      .insert({ ...contato, publico_id: publicoId, usuario_id: userData.user.id })
      .select()
      .single()

    if (err) throw err
    return data
  }

  const excluirContato = async (id: string) => {
    const supabase = getSupabase()
    if (!supabase) return

    const { error: err } = await supabase.from('contatos').delete().eq('id', id)
    if (err) throw err
    contatos.value = contatos.value.filter((c) => c.id !== id)
  }

  return { contatos, isLoading, error, fetchContatos, importarPlanilha, adicionarContato, excluirContato }
}
