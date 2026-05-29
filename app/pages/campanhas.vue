<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})
</script>

<template>
  <ClientOnly>
    <CampanhasManager />
    <template #fallback>
      <AppLoading title="Carregando Campanhas" description="Preparando gerenciamento de campanhas..." />
    </template>
  </ClientOnly>
</template>
