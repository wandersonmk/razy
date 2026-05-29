<template>
  <div class="min-h-screen bg-background">
    <!-- Sidebar -->
    <AppSidebar :is-mobile-open="isMobileMenuOpen" @close-mobile="isMobileMenuOpen = false" />
    
    <!-- Conteúdo principal -->
    <div class="lg:ml-64 min-h-screen flex flex-col">
        <!-- Header principal com título e botões de ação -->
        <header class="bg-card border-b border-border px-6 py-4">
          <div class="flex items-center justify-between">
            <!-- Área esquerda com menu hambúrguer (mobile) e título -->
            <div class="flex items-center space-x-4">
              <!-- Menu Hambúrguer (só aparece no mobile) -->
              <button 
                @click="isMobileMenuOpen = true"
                class="lg:hidden p-2 rounded-lg text-foreground/80 hover:text-foreground hover:bg-muted transition-colors"
                title="Abrir menu"
              >
                <Icon icon="bars" class-name="w-5 h-5" fallback="☰" />
              </button>
            
            <!-- Título -->
            <div>
              <h1 class="text-2xl font-bold text-foreground">{{ pageTitle }}</h1>
              <p class="text-sm text-muted-foreground">{{ pageDescription }}</p>
            </div>
          </div>
          
          <!-- Área de sair -->
          <div class="flex items-center space-x-3 relative">
            <!-- Alternar tema -->
            <ThemeToggle />
            <!-- Botão Sair -->
            <button 
              @click="handleLogout"
              class="flex items-center gap-2 px-3 py-2 rounded-lg text-foreground/70 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 transition-all duration-200 group"
              title="Sair"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 group-hover:scale-110 transition-transform duration-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
              <span class="hidden sm:inline text-sm font-medium">Sair</span>
            </button>
          </div>
        </div>
      </header>

      <!-- Conteúdo da página -->
      <main class="p-6 flex-1">
        <slot />
      </main>
      
      <!-- Footer global -->
      <AppFooter />
    </div>
  </div>
</template>

<script setup lang="ts">
// Estado do menu mobile
const isMobileMenuOpen = ref(false)

// Título dinâmico baseado na rota
const route = useRoute()
const pageTitle = computed(() => {
  switch (route.path) {
    case '/':
      return 'Dashboard'
    case '/pedidos':
      return 'Pedidos'
    case '/cardapio':
      return 'Cardápio'
    case '/clientes':
      return 'Clientes'
    case '/publicos':
      return 'Públicos'
    case '/campanhas':
      return 'Campanhas'
    case '/relatorios':
      return 'Relatórios'
    case '/configuracoes':
      return 'Configurações'
    case '/ajuda':
      return 'Ajuda'
    case '/ajuste-da-ia':
      return 'Ajuste da IA'
    default:
      return 'Dashboard'
  }
})

const pageDescription = computed(() => {
  switch (route.path) {
    case '/':
      return 'Visão geral do sistema'
    case '/pedidos':
      return 'Gerencie todos os pedidos e vendas'
    case '/cardapio':
      return 'Gerencie itens e categorias do cardápio'
    case '/clientes':
      return 'Gerencie todos os seus clientes'
    case '/publicos':
      return 'Gerencie suas listas de contatos para disparo'
    case '/campanhas':
      return 'Crie e gerencie campanhas de disparo via WhatsApp'
    case '/relatorios':
      return 'Gerencie todos os relatórios de disparos'
    case '/configuracoes':
      return 'Configure e gerencie as configurações do sistema'
    case '/ajuda':
      return 'Central de ajuda e guias do sistema'
    case '/ajuste-da-ia':
      return 'Configure as configurações de inteligência artificial'
    default:
      return 'Visão geral do sistema'
  }
})

// Toast
const toast = ref<any>(null)
if (process.client) {
  onMounted(async () => {
    toast.value = await useToastSafe()
  })
}

// Função de logout completa
const handleLogout = async () => {
  try {
    console.log('[Dashboard] Iniciando logout...')
    
    // Limpar localStorage completamente
    if (process.client) {
      localStorage.removeItem('user_email')
      localStorage.removeItem('agzap-auth-token')
      localStorage.removeItem('sb-wynjuzsrydsvkmyhjfhu-auth-token')
      // Limpar todos os itens relacionados ao auth
      Object.keys(localStorage).forEach(key => {
        if (key.includes('auth') || key.includes('supabase') || key.includes('sb-')) {
          localStorage.removeItem(key)
        }
      })
    }
    
    // Limpar estado global
    const globalUser = useState('auth_user')
    const globalSession = useState('auth_session')
    const globalLoading = useState('auth_loading')
    
    globalUser.value = null
    globalSession.value = null
    globalLoading.value = false
    
    console.log('[Dashboard] Estados limpos')
    
    // Mostrar toast de sucesso
    if (toast.value && toast.value.success) {
      toast.value.success('Deslogado com sucesso!', {
        position: 'top-right',
        timeout: 3000,
        closeOnClick: true,
        pauseOnFocusLoss: true,
        pauseOnHover: true,
        draggable: true,
        draggablePercent: 0.6,
        showCloseButtonOnHover: false,
        hideProgressBar: false,
        closeButton: "button",
        icon: true,
        rtl: false
      })
    }
    
    // Pequeno delay para garantir que tudo foi limpo
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // Redirecionar para login com force reload
    console.log('[Dashboard] Redirecionando para login...')
    await navigateTo('/login', { replace: true })
    
    // Force reload para garantir que a página seja totalmente recarregada
    if (process.client) {
      setTimeout(() => {
        window.location.href = '/login'
      }, 100)
    }
    
  } catch (error) {
    console.error('Erro ao fazer logout:', error)
    
    // Mostrar toast de erro
    if (toast.value && toast.value.error) {
      toast.value.error('Erro ao fazer logout. Tente novamente.', {
        position: 'top-right',
        timeout: 5000
      })
    }
    
    // Em caso de erro, force a navegação mesmo assim
    if (process.client) {
      window.location.href = '/login'
    }
  }
}
</script>
