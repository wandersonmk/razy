<script setup lang="ts">
// Aplica middleware de autenticação
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

// Estado de carregamento
const isLoading = ref(true)
const { isLoading: authLoading } = process.client ? useAuth() : { isLoading: ref(false) }

const abaAtiva = ref<'disparos' | 'atendimento'>('disparos')

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
    <div v-else class="space-y-4">
      <div class="flex border-b border-border">
        <button @click="abaAtiva = 'disparos'"
          :class="['py-2.5 px-1 mr-6 text-sm font-medium border-b-2 transition', abaAtiva === 'disparos' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']">
          Disparos
        </button>
        <button @click="abaAtiva = 'atendimento'"
          :class="['py-2.5 px-1 text-sm font-medium border-b-2 transition', abaAtiva === 'atendimento' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']">
          Atendimento
        </button>
      </div>

      <DashboardOverview v-if="abaAtiva === 'disparos'" />
      <div v-else class="bg-card border border-border rounded-lg shadow-sm">
        <RelatorioAtendimento />
      </div>
    </div>
  </div>
</template>
