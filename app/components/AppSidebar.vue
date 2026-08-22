<template>
  <div>
    <!-- Overlay para mobile (só aparece quando menu mobile está aberto) -->
    <div
      v-if="isMobileOpen"
      @click="$emit('close-mobile')"
      class="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
    ></div>

    <!-- Sidebar Desktop (sempre visível em desktop; colapsa pra só ícones) -->
    <div
      class="hidden lg:flex fixed left-0 top-0 h-screen bg-background text-foreground z-50 shadow-2xl flex-col border-r border-border transition-[width] duration-200 ease-in-out"
      :class="colapsado ? 'w-16' : 'w-64'"
    >
      <!-- Header com nome da empresa + botão de colapsar -->
      <div class="flex items-center p-4 border-b border-border" :class="colapsado ? 'justify-center' : 'justify-between'">
        <div v-if="!colapsado" class="flex-1 min-w-0">
          <h1 class="text-lg font-bold truncate">Razy</h1>
          <p class="text-xs text-muted-foreground">Sistema de disparo</p>
        </div>
        <button
          @click="alternar"
          class="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shrink-0"
          :title="colapsado ? 'Expandir menu' : 'Recolher menu'"
        >
          <svg class="w-4 h-4 transition-transform duration-200" :class="colapsado ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7"/>
          </svg>
        </button>
      </div>

      <!-- Menu de navegação -->
      <nav class="px-2.5 py-2 flex-1 overflow-y-auto" :class="colapsado ? '' : 'px-4'">
        <ul class="space-y-1">
          <li v-for="item in NAV_ITEMS" :key="item.to">
            <NuxtLink
              :to="item.to"
              :title="colapsado ? item.label : undefined"
              class="flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors relative"
              :class="[
                $route.path === item.to ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground',
                colapsado ? 'justify-center' : 'gap-3'
              ]"
            >
              <Icon v-if="item.icon.tipo === 'fa'" :icon="item.icon.nome" class-name="w-5 h-5 shrink-0" :fallback="item.icon.fallback || ''" />
              <svg v-else class="w-5 h-5 shrink-0" :fill="item.icon.preenchido ? 'currentColor' : 'none'" :stroke="item.icon.preenchido ? 'none' : 'currentColor'" viewBox="0 0 24 24">
                <path :stroke-linecap="item.icon.preenchido ? undefined : 'round'" :stroke-linejoin="item.icon.preenchido ? undefined : 'round'" :stroke-width="item.icon.preenchido ? undefined : 2" :d="item.icon.d"/>
              </svg>
              <span v-if="!colapsado" class="truncate">{{ item.label }}</span>
            </NuxtLink>
          </li>
        </ul>
      </nav>

      <!-- Seção inferior com informações do usuário e botão sair -->
      <div class="mt-auto border-t border-border bg-muted/30">
        <div class="p-3 flex items-center gap-3" :class="colapsado ? 'justify-center' : ''">
          <div
            v-if="isLoggedIn"
            class="w-8 h-8 shrink-0 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center"
            :title="colapsado ? (userEmail || 'Usuário') : undefined"
          >
            <span class="text-xs font-semibold text-white">{{ userEmail ? userEmail.charAt(0).toUpperCase() : 'U' }}</span>
          </div>
          <div v-else class="w-8 h-8 shrink-0 bg-muted rounded-full flex items-center justify-center animate-pulse">
            <span class="text-xs font-medium text-muted-foreground">...</span>
          </div>
          <div v-if="!colapsado" class="flex-1 min-w-0">
            <p class="text-xs font-medium text-foreground truncate">{{ userEmail || 'Usuário' }}</p>
            <p class="text-xs text-muted-foreground flex items-center">
              <span class="w-1.5 h-1.5 bg-green-500 rounded-full mr-1"></span>
              Online
            </p>
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
          <h1 class="text-lg font-bold truncate">Razy</h1>
          <p class="text-xs text-muted-foreground">Sistema de disparo</p>
        </div>
        <button
          @click="$emit('close-mobile')"
          class="p-2 rounded-lg text-foreground/80 hover:text-foreground hover:bg-muted transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Menu de navegação mobile (mesma lista do desktop) -->
      <nav class="px-4 py-2 flex-1 overflow-y-auto">
        <ul class="space-y-1">
          <li v-for="item in NAV_ITEMS" :key="item.to">
            <NuxtLink
              :to="item.to"
              @click="$emit('close-mobile')"
              class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors relative"
              :class="$route.path === item.to ? 'bg-primary text-primary-foreground' : 'text-foreground/70 hover:bg-muted hover:text-foreground'"
            >
              <Icon v-if="item.icon.tipo === 'fa'" :icon="item.icon.nome" class-name="w-5 h-5 shrink-0" :fallback="item.icon.fallback || ''" />
              <svg v-else class="w-5 h-5 shrink-0" :fill="item.icon.preenchido ? 'currentColor' : 'none'" :stroke="item.icon.preenchido ? 'none' : 'currentColor'" viewBox="0 0 24 24">
                <path :stroke-linecap="item.icon.preenchido ? undefined : 'round'" :stroke-linejoin="item.icon.preenchido ? undefined : 'round'" :stroke-width="item.icon.preenchido ? undefined : 2" :d="item.icon.d"/>
              </svg>
              <span>{{ item.label }}</span>
            </NuxtLink>
          </li>
        </ul>
      </nav>

      <!-- Seção inferior com informações do usuário (mobile) -->
      <div class="mt-auto">
        <div v-if="isLoggedIn" class="p-3 border-t border-border bg-muted/30">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center">
              <span class="text-xs font-semibold text-white">{{ userEmail ? userEmail.charAt(0).toUpperCase() : 'U' }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs font-medium text-foreground truncate">{{ userEmail || 'Usuário' }}</p>
              <p class="text-xs text-green-600 flex items-center">
                <span class="w-1.5 h-1.5 bg-green-500 rounded-full mr-1"></span>
                Online
              </p>
            </div>
          </div>
        </div>
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
import { onMounted, onUnmounted, ref } from 'vue'
import { useSidebar } from '~/composables/useSidebar'

// Props
interface Props {
  isMobileOpen?: boolean
}

withDefaults(defineProps<Props>(), {
  isMobileOpen: false
})

// Emits
defineEmits<{
  'close-mobile': []
}>()

const { colapsado, alternar } = useSidebar()

// Ícone: 'fa' usa o componente <Icon> (FontAwesome); 'svg' usa o path abaixo
// (mesmos ícones/estilo que já existiam, só juntados numa lista só pra não
// duplicar entre o menu desktop e o mobile).
type IconeItem =
  | { tipo: 'fa'; nome: string; fallback?: string }
  | { tipo: 'svg'; d: string; preenchido?: boolean }

const NAV_ITEMS: { to: string; label: string; icon: IconeItem }[] = [
  { to: '/', label: 'Dashboard', icon: { tipo: 'fa', nome: 'home' } },
  { to: '/publicos', label: 'Públicos', icon: { tipo: 'svg', d: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' } },
  { to: '/validar-numeros', label: 'Validar números', icon: { tipo: 'svg', d: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' } },
  { to: '/campanhas', label: 'Campanhas', icon: { tipo: 'svg', preenchido: true, d: 'M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z' } },
  { to: '/follow-up', label: 'Follow-up', icon: { tipo: 'svg', d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' } },
  { to: '/assistente', label: 'Assistente', icon: { tipo: 'svg', d: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' } },
  { to: '/clientes', label: 'Clientes', icon: { tipo: 'fa', nome: 'users' } },
  { to: '/conversas', label: 'Conversas', icon: { tipo: 'svg', d: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-3.5 3.5L9 16z' } },
  { to: '/profissionais', label: 'Profissionais & Canais', icon: { tipo: 'svg', d: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' } },
  { to: '/ia-profissionais', label: 'IA dos Profissionais', icon: { tipo: 'svg', d: 'M13 10V3L4 14h7v7l9-11h-7z' } },
  { to: '/relatorios', label: 'Relatórios', icon: { tipo: 'fa', nome: 'life-ring', fallback: '🆘' } },
  { to: '/configuracoes', label: 'Configurações', icon: { tipo: 'fa', nome: 'cog' } }
]

// Composables - abordagem simplificada
const userEmail = ref<string | null>(null)
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
      const savedEmail = localStorage.getItem('user_email')
      if (savedEmail) {
        userEmail.value = savedEmail
        isLoggedIn.value = true
        return
      }

      const authData = localStorage.getItem('agzap-auth-token')
      if (authData) {
        const parsed = JSON.parse(authData)
        if (parsed.user && parsed.user.email) {
          userEmail.value = parsed.user.email
          isLoggedIn.value = true
          return
        }
      }

      const globalUser = useState('auth_user') as any
      if (globalUser.value && globalUser.value.email) {
        userEmail.value = globalUser.value.email
        isLoggedIn.value = true
        return
      }
    } catch (error) {
      console.error('[AppSidebar] Erro ao verificar sessão:', error)
    }
  }
}
</script>
