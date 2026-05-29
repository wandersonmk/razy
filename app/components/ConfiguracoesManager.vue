<template>
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Header com ícone e descrição -->
    <div class="flex items-center justify-between p-6 border-b border-border">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center">
          <Icon icon="cog" class-name="w-5 h-5 text-white" fallback="" />
        </div>
        <div>
          <h2 class="text-lg font-semibold text-foreground">Configurações do Sistema</h2>
          <p class="text-sm text-muted-foreground">Gerencie as configurações e dados do sistema</p>
        </div>
      </div>
    </div>

    <!-- Conteúdo das configurações -->
    <div class="p-6 space-y-8">
      <CanaisManager />
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

