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
      title="Carregando Cardápio"
      icon="database"
      :pronto="!isLoading"
      @concluido="mostrarLoading = false"
    />

    <!-- Página de Cardápio quando carregado -->
    <CardapioManager v-else />
  </div>
</template>
