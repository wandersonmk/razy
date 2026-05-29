<script setup lang="ts">
// Aplica middleware de autenticação
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

// Estado de carregamento
const isLoading = ref(true)
const { isLoading: authLoading } = process.client ? useAuth() : { isLoading: ref(false) }

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
      title="Carregando Dashboard" 
      description="Preparando visão geral do sistema..."
      icon="database"
    />
    
    <!-- Dashboard quando carregado -->
    <DashboardOverview v-else />
  </div>
</template>
