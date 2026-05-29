import type { SupabaseClient, User, Session } from '@supabase/supabase-js'

export default defineNuxtPlugin(async () => {
  // Só executa no cliente
  if (process.client) {
    console.log('[Auth Plugin] Inicializando...')
    
    // Obter estados existentes ou criar novos
    const user = useState<User | null>('auth_user', () => null)
    const session = useState<Session | null>('auth_session', () => null)
    const loading = useState<boolean>('auth_loading', () => true)
    
    try {
      // Aguardar um pouco para garantir que Supabase está disponível (reduzido)
      await new Promise(resolve => setTimeout(resolve, 200))
      
      const nuxtApp = useNuxtApp()
      
      if (!nuxtApp.$supabase) {
        console.error('[Auth Plugin] Supabase não disponível')
        loading.value = false
        return
      }
      
      const supabase = nuxtApp.$supabase as SupabaseClient
      console.log('[Auth Plugin] Cliente Supabase obtido')
      
      // Verificar se existe uma sessão salva
      const { data, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('[Auth Plugin] Erro ao obter sessão:', error)
        
        // Se o erro é de refresh token inválido, limpar tudo
        if (error.message?.includes('Refresh Token')) {
          console.log('[Auth Plugin] Refresh token inválido, limpando localStorage...')
          localStorage.clear()
          user.value = null
          session.value = null
        }
      } else {
        console.log('[Auth Plugin] Sessão obtida:', { hasSession: !!data.session })
        
        // Atualizar o estado com a sessão atual
        if (data.session) {
          user.value = data.session.user
          session.value = data.session
          console.log('[Auth Plugin] Usuário restaurado:', data.session.user.email)
        } else {
          user.value = null
          session.value = null
          console.log('[Auth Plugin] Nenhuma sessão encontrada')
        }
      }
      
      loading.value = false
      
      // Escutar mudanças de autenticação
      supabase.auth.onAuthStateChange((event: any, newSession: Session | null) => {
        console.log('[Auth Plugin] Auth state changed:', event)
        user.value = newSession?.user ?? null
        session.value = newSession
        console.log('[Auth Plugin] Estado atualizado:', { 
          hasUser: !!user.value, 
          email: user.value?.email 
        })
      })
      
      console.log('[Auth Plugin] Inicialização concluída')
      
    } catch (error) {
      console.error('[Auth Plugin] Erro ao inicializar:', error)
      user.value = null
      session.value = null
      loading.value = false
    }
  }
})
