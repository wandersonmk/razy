<script setup lang="ts">
// Aplica middleware de autenticação
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

// Estado de carregamento
const isLoading = ref(true)
const mostrarLoading = ref(true)
const { isLoading: authLoading } = useAuth()

// Aguarda a autenticação ser carregada e adiciona um delay mínimo para UX
onMounted(async () => {
  await waitForAuthReady(authLoading, { minDelayMs: 220 })
  isLoading.value = false
})
</script>

<template>
  <div>
    <!-- Loading enquanto carrega -->
    <AppLoading
      v-if="mostrarLoading"
      title="Carregando Ajuste da IA"
      :pronto="!isLoading"
      @concluido="mostrarLoading = false"
    />

    <!-- Página de Ajuste da IA quando carregado -->
    <div v-else class="space-y-6">
      <!-- Conteúdo principal -->
      <div class="bg-card border border-border rounded-lg p-6">
        <div class="flex items-center justify-center h-64">
          <div class="text-center">
            <div class="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
              <svg class="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
              </svg>
            </div>
            <h3 class="text-lg font-medium text-foreground mb-2">Página em Construção</h3>
            <p class="text-muted-foreground">As configurações de IA serão implementadas em breve.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
