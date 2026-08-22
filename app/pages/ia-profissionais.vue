<script setup lang="ts">
import { ref } from 'vue'
definePageMeta({ middleware: 'auth', layout: 'dashboard' })

const route = useRoute()
const router = useRouter()

const modo = ref<'lista' | 'editor'>(route.query.profissional ? 'editor' : 'lista')
const profissionalEditandoId = ref<string | null>((route.query.profissional as string) || null)

function configurar(id: string) {
  profissionalEditandoId.value = id
  modo.value = 'editor'
  router.replace({ query: { profissional: id } })
}

function voltar() {
  modo.value = 'lista'
  profissionalEditandoId.value = null
  router.replace({ query: {} })
}
</script>

<template>
  <ClientOnly>
    <AssistentesProfissionaisLista v-if="modo === 'lista'" @configurar="configurar" />
    <AssistenteProfissionalManager v-else-if="profissionalEditandoId" :profissional-id="profissionalEditandoId" @voltar="voltar" @salvo="voltar" />
    <template #fallback>
      <div class="flex items-center justify-center py-20 text-muted-foreground text-sm">Carregando IA dos Profissionais...</div>
    </template>
  </ClientOnly>
</template>
