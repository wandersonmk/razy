export default defineNuxtRouteMiddleware(async (to, from) => {
  // No servidor, não precisa verificar autenticação detalhada
  if (process.server) {
    return
  }
  
  try {
    const { isAuthenticated, user, isLoading } = useAuth()
    
    console.log('Guest middleware - Estado auth:', { 
      isAuthenticated: isAuthenticated.value, 
      hasUser: !!user.value,
      isLoading: isLoading.value,
      email: user.value?.email 
    })
    
    // Aguarda apenas um curto período se ainda estiver carregando
    if (isLoading.value) {
      await new Promise(resolve => setTimeout(resolve, 500))
    }
    
    console.log('Guest middleware - Após loading:', { 
      isAuthenticated: isAuthenticated.value, 
      hasUser: !!user.value,
      isLoading: isLoading.value,
      email: user.value?.email 
    })
    
    // APENAS redireciona se estiver REALMENTE autenticado (com sessão válida)
    if (isAuthenticated.value && user.value) {
      console.log('Guest middleware: Usuário autenticado, redirecionando para /')
      return navigateTo('/')
    }
    
    // Se não estiver autenticado, permite acesso à página de login
    console.log('Guest middleware: Usuário não autenticado, permitindo acesso ao login')
  } catch (error) {
    // Se houver erro na inicialização, permite acesso à página de login
    console.error('Erro no middleware guest:', error)
    // Não redireciona, permite que o usuário veja a página de login
  }
})
