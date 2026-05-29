export function useEmpresa() {
  // Estado global para o nome da empresa
  const nomeEmpresa = useState<string | null>('empresa_nome', () => null)
  const isLoadingEmpresa = useState<boolean>('empresa_loading', () => false)

  // Busca SIMPLES e DIRETA do nome da empresa
  async function buscarNomeEmpresa() {
    if (!process.client) return

    try {
      isLoadingEmpresa.value = true
      const supabase = useSupabaseClient()
      
      // Pega o usuário atual da sessão do Supabase diretamente
      const { data: { user } } = await supabase.auth.getUser()
      
      if (!user?.id) {
        console.log('Usuário não está logado')
        nomeEmpresa.value = null
        return
      }

      console.log('Buscando empresa para usuário:', user.id)
      
      // Busca a empresa no banco
      const { data, error } = await supabase
        .from('empresas')
        .select('nome')
        .eq('usuario_id', user.id)
        .single()

      if (error) {
        console.error('Erro ao buscar empresa:', error)
        nomeEmpresa.value = null
        return
      }

      console.log('Nome da empresa encontrado:', data?.nome)
      nomeEmpresa.value = data?.nome || null
      
    } catch (err) {
      console.error('Erro:', err)
      nomeEmpresa.value = null
    } finally {
      isLoadingEmpresa.value = false
    }
  }

  return {
    nomeEmpresa: readonly(nomeEmpresa),
    isLoadingEmpresa: readonly(isLoadingEmpresa),
    buscarNomeEmpresa
  }
}
