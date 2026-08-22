<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
  layout: 'dashboard'
})

const mostrarLoading = ref(true)
const pronto = ref(false)
onMounted(() => { pronto.value = true })
</script>

<template>
  <div>
    <AppLoading
      v-if="mostrarLoading"
      title="Carregando Campanhas"
      icon="bolt"
      :pronto="pronto"
      @concluido="mostrarLoading = false"
    />
    <CampanhasManager v-else />
  </div>
</template>
