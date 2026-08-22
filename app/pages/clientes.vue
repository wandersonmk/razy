<script setup lang="ts">
// Aplica middleware de autenticação
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

// Estado de carregamento
const isLoading = ref(true)
const mostrarLoading = ref(true)
let authLoading: any = ref(false)
const isClient = typeof window !== 'undefined'

if (isClient) {
  // Só executa useAuth no cliente
  const auth = useAuth()
  authLoading = auth.isLoading

  onMounted(async () => {
    await waitForAuthReady(authLoading, { minDelayMs: 250 })
    isLoading.value = false
  })
} else {
  isLoading.value = false
}
</script>

<template>
  <div>
    <!-- Sempre mostra loading até o client terminar de carregar -->
    <AppLoading
      v-if="mostrarLoading"
      title="Carregando Clientes"
      icon="database"
      :pronto="!isLoading && isClient"
      @concluido="mostrarLoading = false"
    />
    <!-- Conteúdo só aparece após carregamento client-side -->
    <div v-else class="space-y-6">
      <ClientesManager />
    </div>
  </div>
</template>
