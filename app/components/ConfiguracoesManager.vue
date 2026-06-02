<template>
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Header -->
    <div class="flex items-center p-6 border-b border-border gap-3">
      <div class="w-10 h-10 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center">
        <Icon icon="cog" class-name="w-5 h-5 text-white" fallback="" />
      </div>
      <div>
        <h2 class="text-lg font-semibold text-foreground">Configurações do Sistema</h2>
        <p class="text-sm text-muted-foreground">Canais de envio e integrações</p>
      </div>
    </div>

    <!-- Abas -->
    <div class="flex border-b border-border px-6">
      <button
        @click="aba = 'canais'"
        :class="['py-3 px-1 mr-6 text-sm font-medium border-b-2 transition', aba === 'canais' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
      >
        Canais WhatsApp
      </button>
      <button
        @click="aba = 'integracoes'"
        :class="['py-3 px-1 mr-6 text-sm font-medium border-b-2 transition', aba === 'integracoes' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
      >
        Integrações
      </button>
      <button
        @click="aba = 'apagar_metricas'"
        :class="['py-3 px-1 text-sm font-medium border-b-2 transition', aba === 'apagar_metricas' ? 'border-red-500 text-red-600 dark:text-red-400' : 'border-transparent text-muted-foreground hover:text-foreground']"
      >
        Apagar métricas
      </button>
    </div>

    <!-- Conteúdo -->
    <div class="p-6">
      <div v-if="aba === 'canais'">
        <CanaisManager />
      </div>

      <div v-if="aba === 'integracoes'" class="space-y-4">
        <div>
          <h3 class="text-base font-semibold text-foreground">Integrações</h3>
          <p class="text-xs text-muted-foreground mt-0.5">Configure as chaves de API dos serviços externos utilizados pela IA.</p>
        </div>
        <IntegracaoOpenAI />
      </div>

      <div v-if="aba === 'apagar_metricas'">
        <ApagarMetricasManager />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const aba = ref<'canais' | 'integracoes' | 'apagar_metricas'>('canais')
</script>
