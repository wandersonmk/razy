<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})
</script>

<template>
  <ClientOnly>
    <PublicosManager />
    <template #fallback>
      <AppLoading title="Carregando Públicos" description="Preparando gerenciamento de públicos..." />
    </template>
  </ClientOnly>
</template>
