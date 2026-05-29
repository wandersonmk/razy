export default defineNuxtRouteMiddleware(async (to, from) => {
  // No servidor, não precisa verificar autenticação detalhada
  if (process.server) {
    return
  }
  
  try {
    // Evita bloquear a navegacao por muito tempo em dispositivos lentos.
    await new Promise(resolve => setTimeout(resolve, 120))
    
    const { isAuthenticated, user, isLoading } = useAuth()
    
    // Aguarda o carregamento ser concluído se ainda estiver carregando
    let attempts = 0
    const maxAttempts = 8
    
    while (isLoading.value && attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 50))
      attempts++
    }
    
    // Se ainda não está autenticado, tenta verificar diretamente no Supabase
    if (!isAuthenticated.value || !user.value) {
      try {
        const nuxtApp = useNuxtApp()
        if (nuxtApp.$supabase) {
          const supabase = nuxtApp.$supabase as any
          const { data } = await supabase.auth.getSession()
          if (data.session && data.session.user) {
            // A sessão existe, permitir acesso e deixar o plugin atualizar o estado
            return
          }
        }
      } catch (error) {
        console.error('[Auth Middleware] Erro ao verificar sessão diretamente:', error)
      }
    }
    
    // Se não está autenticado, redireciona para login
    if (!isAuthenticated.value || !user.value) {
      return navigateTo('/login')
    }
  } catch (error) {
    // Se houver erro na inicialização, redireciona para login
    console.error('[Auth Middleware] Erro:', error)
    return navigateTo('/login')
  }
})
