<template>
  <div class="min-h-screen bg-background">
    <!-- Sidebar -->
    <AppSidebar :is-mobile-open="isMobileMenuOpen" @close-mobile="isMobileMenuOpen = false" />
    
    <!-- Conteúdo principal -->
    <div class="min-h-screen flex flex-col transition-[margin] duration-200 ease-in-out" :class="colapsado ? 'lg:ml-16' : 'lg:ml-64'">
        <!-- Banner de alerta: conta OpenAI sem saldo (fixo no topo do conteúdo) -->
        <AlertaSaldoOpenAI />

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
import { useSidebar } from '~/composables/useSidebar'

// Estado do menu mobile
const isMobileMenuOpen = ref(false)

// Menu lateral colapsável — estado compartilhado com o AppSidebar.
// Na página de Conversas ele recolhe sozinho (ganha espaço pra lista+chat);
// o dono pode expandir de novo a qualquer momento clicando no botão.
const { colapsado, colapsar, restaurar } = useSidebar()

onMounted(() => {
  restaurar()
})

// Título dinâmico baseado na rota
const route = useRoute()
watch(
  () => route.path,
  (novo, antigo) => {
    if (novo === '/conversas' && antigo !== '/conversas') colapsar()
  }
)
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
    case '/validar-numeros':
      return 'Validador de números'
    case '/campanhas':
      return 'Campanhas'
    case '/relatorios':
      return 'Relatórios'
    case '/configuracoes':
      return 'Configurações'
    case '/ajuste-da-ia':
      return 'Ajuste da IA'
    case '/follow-up':
      return 'Follow-up'
    case '/assistente':
      return 'Assistente'
    case '/conversas':
      return 'Conversas'
    case '/profissionais':
      return 'Profissionais & Canais'
    case '/ia-profissionais':
      return 'IA dos Profissionais'
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
    case '/validar-numeros':
      return 'Suba sua planilha, verificamos quais números têm WhatsApp e separamos os válidos dos inválidos'
    case '/campanhas':
      return 'Crie e gerencie campanhas de disparo via WhatsApp'
    case '/relatorios':
      return 'Gerencie todos os relatórios de disparos'
    case '/configuracoes':
      return 'Configure e gerencie as configurações do sistema'
    case '/ajuste-da-ia':
      return 'Configure as configurações de inteligência artificial'
    case '/follow-up':
      return 'Reengaje contatos que não responderam com sequências automáticas'
    case '/assistente':
      return 'Configure o atendimento automático por IA e o encaminhamento ao atendente'
    case '/conversas':
      return 'Acompanhe o atendimento dos profissionais em tempo real'
    case '/profissionais':
      return 'Cadastre profissionais e conecte o WhatsApp de cada um'
    case '/ia-profissionais':
      return 'Ligue e configure a IA de cada profissional, separada do assistente principal'
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
