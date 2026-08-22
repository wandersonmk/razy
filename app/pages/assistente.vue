<script setup lang="ts">
import { ref } from 'vue'
definePageMeta({ middleware: 'auth', layout: 'dashboard' })

const mostrarLoading = ref(true)
const pronto = ref(false)
onMounted(() => { pronto.value = true })

const modo = ref<'lista' | 'editor'>('lista')
const assistenteEditandoId = ref<string | null>(null)

function editar(id: string) {
  assistenteEditandoId.value = id
  modo.value = 'editor'
}

function voltar() {
  modo.value = 'lista'
  assistenteEditandoId.value = null
}
</script>

<template>
  <div>
    <AppLoading
      v-if="mostrarLoading"
      title="Carregando Assistente"
      icon="robot"
      :pronto="pronto"
      @concluido="mostrarLoading = false"
    />
    <template v-else>
      <AssistentesLista v-if="modo === 'lista'" @editar="editar" />
      <AssistenteManager v-else :assistente-id="assistenteEditandoId" @voltar="voltar" @salvo="voltar" />
    </template>
  </div>
</template>
