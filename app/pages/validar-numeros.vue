<script setup lang="ts">
// Aplica middleware de autenticação
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

const isLoading = ref(true)
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
      v-if="isLoading || !isClient"
      title="Carregando Validador"
      description="Preparando a validação de números..."
      icon="check-circle"
    />
    <div v-else class="space-y-6">
      <ValidadorNumeros />
    </div>
  </div>
</template>
