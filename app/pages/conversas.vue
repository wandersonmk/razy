<script setup lang="ts">
definePageMeta({ middleware: 'auth', layout: 'dashboard' })

const mostrarLoading = ref(true)
const pronto = ref(false)
onMounted(() => { pronto.value = true })
</script>

<template>
  <div>
    <AppLoading
      v-if="mostrarLoading"
      title="Carregando Conversas"
      icon="comments"
      :pronto="pronto"
      @concluido="mostrarLoading = false"
    />
    <ConversasManager v-else />
  </div>
</template>
