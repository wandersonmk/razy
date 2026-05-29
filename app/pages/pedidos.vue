<script setup lang="ts">
// Aplica middleware de autenticação
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

// Estado de carregamento
const isLoading = ref(true)
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
      v-if="isLoading"
      title="Carregando Pedidos" 
      description="Preparando gerenciamento de pedidos..."
      icon="database"
    />
    
    <!-- Página de Pedidos quando carregado -->
    <PedidosManager v-else />
  </div>
</template>
