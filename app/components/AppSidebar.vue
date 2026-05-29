<template>
  <div>
    <!-- Overlay para mobile (só aparece quando menu mobile está aberto) -->
    <div 
      v-if="isMobileOpen"
      @click="$emit('close-mobile')"
      class="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
    ></div>

    <!-- Sidebar Desktop (sempre visível em desktop) -->
    <div 
      class="hidden lg:flex fixed left-0 top-0 h-screen w-64 bg-background text-foreground z-50 shadow-2xl flex-col border-r border-border"
    >
      <!-- Header com nome da empresa -->
      <div class="flex items-center p-4 border-b border-border">
        <div class="flex-1 min-w-0">
          <h1 class="text-lg font-bold truncate">
            Razy
          </h1>
          <p class="text-xs text-muted-foreground">Sistema de disparo</p>
        </div>
      </div>

      <!-- Menu de navegação -->
      <nav class="px-4 py-2 flex-1 overflow-y-auto">
        <ul class="space-y-1">
          <!-- Dashboard -->
          <li>
            <NuxtLink 
              to="/"
              class="flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'"
            >
              <Icon icon="home" class-name="w-5 h-5 mr-3" fallback="" />
              <span>Dashboard</span>
            </NuxtLink>
          </li>

          <!-- Públicos -->
          <li>
            <NuxtLink
              to="/publicos"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/publicos' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'"
            >
              <svg class="w-5 h-5 mr-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              <span>Públicos</span>
            </NuxtLink>
          </li>

          <!-- Campanhas -->
          <li>
            <NuxtLink
              to="/campanhas"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/campanhas' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'"
            >
              <svg class="w-5 h-5 mr-3 shrink-0" fill="currentColor" viewBox="0 0 24 24">
                <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/>
              </svg>
              <span>Campanhas</span>
            </NuxtLink>
          </li>

          <!-- Clientes -->
          <li>
            <NuxtLink
              to="/clientes"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/clientes' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'"
            >
              <Icon icon="users" class-name="w-5 h-5 mr-3" fallback="" />
              <span>Clientes</span>
            </NuxtLink>
          </li>

          <!-- Relatórios -->
          <li>
            <NuxtLink
              to="/relatorios"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/relatorios' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'"
            >
              <Icon icon="life-ring" class-name="w-5 h-5 mr-3" fallback="🆘" />
              <span>Relatórios</span>
            </NuxtLink>
          </li>

          <!-- Configurações -->
          <li>
            <NuxtLink
              to="/configuracoes"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/configuracoes' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'"
            >
              <Icon icon="cog" class-name="w-5 h-5 mr-3" fallback="" />
              <span>Configurações</span>
            </NuxtLink>
          </li>

          <!-- Ajuda -->
          <li>
            <NuxtLink
              to="/ajuda"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/ajuda' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'"
            >
              <Icon icon="question-circle" class-name="w-5 h-5 mr-3" fallback="" />
              <span>Ajuda</span>
            </NuxtLink>
          </li>
        </ul>
      </nav>

      <!-- Seção inferior com informações do usuário e botão sair -->
      <div class="mt-auto">
        <!-- Informações do usuário -->
        <div v-if="isLoggedIn" class="p-3 border-t border-border bg-muted/30">
          <div class="flex items-center space-x-3 mb-3">
            <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center">
              <span class="text-xs font-semibold text-white">
                {{ userEmail ? userEmail.charAt(0).toUpperCase() : 'U' }}
              </span>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs font-medium text-foreground truncate">
                {{ userEmail || 'Usuário' }}
              </p>
              <p class="text-xs text-muted-foreground flex items-center">
                <span class="w-1.5 h-1.5 bg-green-500 rounded-full mr-1"></span>
                Online
              </p>
            </div>
          </div>
        </div>
        
        <!-- Loading state quando usuário ainda está carregando -->
        <div v-else class="p-3 border-t border-border bg-muted/30">
          <div class="flex items-center space-x-3 mb-3">
            <div class="w-8 h-8 bg-muted rounded-full flex items-center justify-center animate-pulse">
              <span class="text-xs font-medium text-muted-foreground">...</span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="h-3 bg-muted rounded animate-pulse mb-1"></div>
              <div class="h-2.5 bg-muted/70 rounded animate-pulse w-10"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Sidebar Mobile (só aparece quando isMobileOpen for true) -->
    <div 
      :class="isMobileOpen ? 'translate-x-0' : '-translate-x-full'"
      class="lg:hidden fixed left-0 top-0 h-screen w-64 bg-background text-foreground z-50 shadow-2xl flex-col border-r border-border transition-transform duration-300 ease-in-out flex"
    >
      <!-- Header com nome da empresa e botão fechar -->
      <div class="flex items-center justify-between p-4 border-b border-border">
        <div class="flex-1 min-w-0">
          <h1 class="text-lg font-bold truncate">
            Razy
          </h1>
          <p class="text-xs text-muted-foreground">Sistema de disparo</p>
        </div>
        
        <!-- Botão fechar -->
        <button 
          @click="$emit('close-mobile')"
          class="p-2 rounded-lg text-foreground/80 hover:text-foreground hover:bg-muted transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Menu de navegação mobile (mesmo conteúdo do desktop) -->
      <nav class="px-4 py-2 flex-1 overflow-y-auto">
        <ul class="space-y-1">
          <!-- Dashboard -->
          <li>
            <NuxtLink 
              to="/"
              @click="$emit('close-mobile')"
              class="flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'"
            >
              <Icon icon="home" class-name="w-5 h-5 mr-3" fallback="" />
              <span>Dashboard</span>
            </NuxtLink>
          </li>

          <!-- Públicos -->
          <li>
            <NuxtLink to="/publicos" @click="$emit('close-mobile')"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/publicos' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'">
              <svg class="w-5 h-5 mr-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              <span>Públicos</span>
            </NuxtLink>
          </li>

          <!-- Campanhas -->
          <li>
            <NuxtLink to="/campanhas" @click="$emit('close-mobile')"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/campanhas' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'">
              <svg class="w-5 h-5 mr-3 shrink-0" fill="currentColor" viewBox="0 0 24 24">
                <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/>
              </svg>
              <span>Campanhas</span>
            </NuxtLink>
          </li>

          <!-- Clientes -->
          <li>
            <NuxtLink to="/clientes" @click="$emit('close-mobile')"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/clientes' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'">
              <Icon icon="users" class-name="w-5 h-5 mr-3" fallback="" />
              <span>Clientes</span>
            </NuxtLink>
          </li>

          <!-- Relatórios -->
          <li>
            <NuxtLink to="/relatorios" @click="$emit('close-mobile')"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/relatorios' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'">
              <Icon icon="file-alt" class-name="w-5 h-5 mr-3" fallback="" />
              <span>Relatórios</span>
            </NuxtLink>
          </li>

          <!-- Configurações -->
          <li>
            <NuxtLink to="/configuracoes" @click="$emit('close-mobile')"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/configuracoes' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'">
              <Icon icon="cog" class-name="w-5 h-5 mr-3" fallback="" />
              <span>Configurações</span>
            </NuxtLink>
          </li>

          <!-- Ajuda -->
          <li>
            <NuxtLink to="/ajuda" @click="$emit('close-mobile')"
              class="flex items-center w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative"
              :class="$route.path === '/ajuda' ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'">
              <Icon icon="question-circle" class-name="w-5 h-5 mr-3" fallback="" />
              <span>Ajuda</span>
            </NuxtLink>
          </li>
        </ul>
      </nav>

      <!-- Seção inferior com informações do usuário (mobile) -->
      <div class="mt-auto">
        <!-- Informações do usuário -->
        <div v-if="isLoggedIn" class="p-3 border-t border-border bg-muted/30">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center">
              <span class="text-xs font-semibold text-white">
                {{ userEmail ? userEmail.charAt(0).toUpperCase() : 'U' }}
              </span>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs font-medium text-foreground truncate">
                {{ userEmail || 'Usuário' }}
              </p>
              <p class="text-xs text-green-600 flex items-center">
                <span class="w-1.5 h-1.5 bg-green-500 rounded-full mr-1"></span>
                Online
              </p>
            </div>
          </div>
        </div>
        
        <!-- Loading state quando usuário ainda está carregando -->
        <div v-else class="p-3 border-t border-border bg-muted/30">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-muted rounded-full flex items-center justify-center animate-pulse">
              <span class="text-xs font-medium text-muted-foreground">...</span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="h-3 bg-muted rounded animate-pulse mb-1"></div>
              <div class="h-2.5 bg-muted/70 rounded animate-pulse w-10"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

// Props
interface Props {
  isMobileOpen?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isMobileOpen: false
})

// Emits
const emit = defineEmits<{
  'close-mobile': []
}>()

// Composables - abordagem simplificada
const userEmail = ref<string | null>(null)
const userName = ref<string | null>(null)
const isLoggedIn = ref(false)

// Toast e montagem SIMPLES
const toast = ref<any>(null)
if (process.client) {
  onMounted(async () => {
    toast.value = await useToastSafe()
    checkUserSession()
  })
}

// Atualizar dados quando página ficar visível - SIMPLES
if (process.client) {
  // Escutar mudanças de visibilidade da página para atualizar dados
  const handleVisibilityChange = async () => {
    if (!document.hidden) {
      checkUserSession()
    }
  }
  
  onMounted(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
  })
  
  onUnmounted(() => {
    document.removeEventListener('visibilitychange', handleVisibilityChange)
  })
}

// Função para verificar sessão do usuário
const checkUserSession = () => {
  if (process.client) {
    try {
      // Método mais simples - verificar email salvo
      const savedEmail = localStorage.getItem('user_email')
      if (savedEmail) {
        userEmail.value = savedEmail
        isLoggedIn.value = true
        console.log('[AppSidebar] Email encontrado:', savedEmail)
        return
      }
      
      // Tentar pegar do localStorage do Supabase
      const authData = localStorage.getItem('agzap-auth-token')
      if (authData) {
        const parsed = JSON.parse(authData)
        if (parsed.user && parsed.user.email) {
          userEmail.value = parsed.user.email
          isLoggedIn.value = true
          console.log('[AppSidebar] Usuário encontrado no Supabase:', userEmail.value)
          return
        }
      }
      
      // Tentar pegar do estado global se disponível
      const globalUser = useState('auth_user') as any
      if (globalUser.value && globalUser.value.email) {
        userEmail.value = globalUser.value.email
        isLoggedIn.value = true
        console.log('[AppSidebar] Usuário do estado global:', userEmail.value)
        return
      }
      
      console.log('[AppSidebar] Nenhum usuário encontrado')
    } catch (error) {
      console.error('[AppSidebar] Erro ao verificar sessão:', error)
    }
  }
}
</script>

