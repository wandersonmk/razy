<script setup lang="ts">
import { ref } from 'vue'
definePageMeta({ middleware: 'auth', layout: 'dashboard' })

const route = useRoute()
const router = useRouter()

const mostrarLoading = ref(true)
const pronto = ref(false)
onMounted(() => { pronto.value = true })

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
  <div>
    <AppLoading
      v-if="mostrarLoading"
      title="Carregando IA dos Profissionais"
      icon="robot"
      :pronto="pronto"
      @concluido="mostrarLoading = false"
    />
    <template v-else>
      <AssistentesProfissionaisLista v-if="modo === 'lista'" @configurar="configurar" />
      <AssistenteProfissionalManager v-else-if="profissionalEditandoId" :profissional-id="profissionalEditandoId" @voltar="voltar" @salvo="voltar" />
    </template>
  </div>
</template>
