<template>
  <div class="min-h-screen bg-background relative overflow-hidden flex flex-col" style="cursor: auto;">
    <!-- Gradientes de fundo decorativos -->
    <div class="absolute inset-0 pointer-events-none">
      <!-- Gradiente superior esquerdo -->
      <div class="absolute top-0 left-0 w-96 h-96 bg-gradient-to-br from-blue-900/30 via-blue-800/20 to-transparent rounded-full blur-3xl transform -translate-x-1/2 -translate-y-1/2"></div>
      
      <!-- Gradiente superior direito -->
      <div class="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-blue-900/25 via-blue-700/15 to-transparent rounded-full blur-3xl transform translate-x-1/3 -translate-y-1/3"></div>
      
      <!-- Gradiente inferior esquerdo -->
      <div class="absolute bottom-0 left-0 w-72 h-72 bg-gradient-to-tr from-indigo-900/20 via-blue-800/15 to-transparent rounded-full blur-3xl transform -translate-x-1/3 translate-y-1/3"></div>
      
      <!-- Gradiente inferior direito -->
      <div class="absolute bottom-0 right-0 w-88 h-88 bg-gradient-to-tl from-blue-900/25 via-blue-800/20 to-transparent rounded-full blur-3xl transform translate-x-1/4 translate-y-1/4"></div>
      
      <!-- Gradiente central sutil -->
      <div class="absolute top-1/2 left-1/2 w-96 h-96 bg-gradient-to-r from-transparent via-blue-900/10 to-transparent rounded-full blur-2xl transform -translate-x-1/2 -translate-y-1/2"></div>
      
      <!-- Efeito de profundidade adicional -->
      <div class="absolute top-1/4 right-1/4 w-64 h-64 bg-gradient-to-bl from-blue-800/15 via-blue-900/10 to-transparent rounded-full blur-xl opacity-60"></div>
      <div class="absolute bottom-1/4 left-1/4 w-56 h-56 bg-gradient-to-tr from-indigo-800/12 via-blue-700/8 to-transparent rounded-full blur-xl opacity-70"></div>
    </div>
    
    <!-- Conteúdo principal -->
    <div class="relative z-10 flex-1">
      <main>
        <slot />
      </main>
    </div>
    
    <!-- Footer global -->
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
// Layout padrão que inclui o header em todas as páginas internas
</script>
