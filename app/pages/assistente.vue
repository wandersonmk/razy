<script setup lang="ts">
import { ref } from 'vue'
definePageMeta({ middleware: 'auth', layout: 'dashboard' })

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
  <ClientOnly>
    <AssistentesLista v-if="modo === 'lista'" @editar="editar" />
    <AssistenteManager v-else :assistente-id="assistenteEditandoId" @voltar="voltar" @salvo="voltar" />
    <template #fallback>
      <div class="flex items-center justify-center py-20 text-muted-foreground text-sm">Carregando Assistentes...</div>
    </template>
  </ClientOnly>
</template>
