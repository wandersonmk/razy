<script setup lang="ts">
// Aplica middleware de autenticação
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

const isLoading = ref(true)
const mostrarLoading = ref(true)
let authLoading: any = ref(false)
const isClient = typeof window !== 'undefined'

if (isClient) {
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
    <AppLoading
      v-if="mostrarLoading"
      title="Carregando Validador"
      icon="check-circle"
      :pronto="!isLoading && isClient"
      @concluido="mostrarLoading = false"
    />
    <div v-else class="space-y-6">
      <ValidadorNumeros />
    </div>
  </div>
</template>
