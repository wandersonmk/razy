<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useConversas } from '~/composables/useConversas'

// conversas.photo guarda o PATH dentro do bucket (não uma URL pronta) — o
// bucket é privado, então sempre resolvemos uma signed URL na hora de exibir.
const props = defineProps<{ nome?: string | null; numero?: string | null; photo?: string | null; sizeClass?: string }>()

const { urlAssinadaMidia } = useConversas()
const url = ref<string | null>(null)

async function carregar() {
  url.value = props.photo ? await urlAssinadaMidia(props.photo) : null
}
onMounted(carregar)
watch(() => props.photo, carregar)

function iniciais(): string {
  const base = (props.nome || props.numero || '?').trim()
  const partes = base.split(/\s+/)
  return ((partes[0]?.[0] || '') + (partes[1]?.[0] || '')).toUpperCase() || '?'
}
</script>

<template>
  <div :class="['rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center text-white font-semibold shrink-0 overflow-hidden', sizeClass || 'w-10 h-10 text-sm']">
    <img v-if="url" :src="url" class="w-full h-full object-cover" alt="" />
    <span v-else>{{ iniciais() }}</span>
  </div>
</template>
