<script setup lang="ts">
// Aplica middleware de autenticação
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

// Estado de carregamento
const isLoading = ref(true)
let authLoading = ref(true)

if (process.client) {
  const { isLoading: _authLoading } = useAuth()
  authLoading = _authLoading

  onMounted(async () => {
    await waitForAuthReady(authLoading, { minDelayMs: 220 })
    isLoading.value = false
  })
}
</script>

<template>
  <div>
    <!-- Loading enquanto carrega -->
    <AppLoading 
      v-if="isLoading" 
      title="Carregando Ajuda"
      description="Preparando a central de ajuda..."
    />
    
    <!-- Página de Ajuda quando carregado -->
    <div v-else class="space-y-6">
      <!-- Componente de ajuda (client-only) -->
      <ClientOnly>
        <AjudaManager />
        <template #fallback>
          <div class="bg-card border border-border rounded-lg p-6">
            <div class="flex items-center justify-center h-64">
              <div class="text-center">
                <div class="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
                  <svg class="w-8 h-8 text-muted-foreground animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                </div>
                <h3 class="text-lg font-medium text-foreground mb-2">Carregando Ajuda</h3>
                <p class="text-muted-foreground">Preparando a interface...</p>
              </div>
            </div>
          </div>
        </template>
      </ClientOnly>
    </div>
  </div>
</template>
