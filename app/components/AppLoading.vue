<template>
  <div class="fixed inset-0 bg-background/95 backdrop-blur-sm z-50 flex items-center justify-center">
    <div class="flex flex-col items-center gap-6 p-8">
      <div class="w-12 h-12 bg-muted/40 rounded-xl flex items-center justify-center">
        <Icon :icon="icon" class-name="w-6 h-6 text-blue-500 animate-spin" fallback="" />
      </div>

      <!-- Spinner principal com gradiente -->
      <div class="relative">
        <!-- Círculo de fundo -->
        <div class="w-20 h-20 border-4 border-muted/30 rounded-full"></div>
        <!-- Círculo animado com gradiente -->
        <div class="absolute top-0 left-0 w-20 h-20 border-4 rounded-full border-transparent border-t-blue-500 border-r-purple-500 animate-spin"></div>
        <!-- Círculo interno menor -->
        <div class="absolute top-2 left-2 w-16 h-16 border-2 border-muted/20 rounded-full"></div>
      </div>
      
      <!-- Texto de carregamento -->
      <div class="text-center max-w-sm">
        <h3 class="text-xl font-bold text-foreground mb-2">{{ title }}</h3>
        <p class="text-muted-foreground">{{ description }}</p>
      </div>
      
      <!-- Barra de progresso animada -->
      <div class="w-48 h-1 bg-muted rounded-full overflow-hidden">
        <div class="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full animate-pulse"></div>
      </div>
      
      <!-- Pontos animados -->
      <div class="flex gap-2">
        <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
        <div class="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style="animation-delay: 200ms"></div>
        <div class="w-2 h-2 bg-pink-500 rounded-full animate-bounce" style="animation-delay: 400ms"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Props opcionais para customização
interface Props {
  title?: string
  description?: string
  icon?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Carregando Dashboard',
  description: 'Aguarde um momento...',
  icon: 'database'
})
</script>

