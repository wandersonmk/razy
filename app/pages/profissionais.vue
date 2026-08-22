<script setup lang="ts">
definePageMeta({ middleware: 'auth', layout: 'dashboard' })
</script>

<template>
  <ClientOnly>
    <ProfissionaisManager />
    <template #fallback>
      <div class="flex items-center justify-center py-20 text-muted-foreground text-sm">Carregando Profissionais...</div>
    </template>
  </ClientOnly>
</template>
