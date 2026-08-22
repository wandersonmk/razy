<script setup lang="ts">
import { ref, watch } from 'vue'
import { useCanais } from '~/composables/useCanais'

const props = defineProps<{ show: boolean; instanciaId: string | null; nome: string | null }>()
const emit = defineEmits<{ close: [] }>()

const { gerarLink, revogarLink } = useCanais()

const carregando = ref(false)
const revogando = ref(false)
const url = ref<string | null>(null)
const erro = ref<string | null>(null)
const copiado = ref(false)

let toast: any
onMounted(async () => { toast = await useToastSafe() })

async function carregar() {
  if (!props.instanciaId) return
  carregando.value = true
  erro.value = null
  url.value = null
  try {
    const r = await gerarLink(props.instanciaId)
    url.value = r.url
  } catch (e: any) {
    erro.value = e?.message || 'Erro ao gerar o link'
  } finally {
    carregando.value = false
  }
}

watch(() => props.show, (val) => {
  if (val) { copiado.value = false; carregar() }
})

async function copiar() {
  if (!url.value) return
  try {
    await navigator.clipboard.writeText(url.value)
    copiado.value = true
    toast?.success('Link copiado!')
    setTimeout(() => { copiado.value = false }, 2000)
  } catch {
    toast?.error('Não foi possível copiar — selecione e copie manualmente')
  }
}

async function revogar() {
  if (!props.instanciaId) return
  revogando.value = true
  try {
    await revogarLink(props.instanciaId)
    toast?.success('Link revogado')
    await carregar()
  } catch (e: any) {
    toast?.error(e?.message || 'Erro ao revogar o link')
  } finally {
    revogando.value = false
  }
}

function fechar() {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      @click.self="fechar"
    >
      <div class="bg-card border border-border rounded-2xl w-full max-w-sm shadow-2xl overflow-hidden">
        <div class="flex items-start gap-3 p-5 border-b border-border">
          <div class="w-10 h-10 bg-violet-500/10 rounded-xl flex items-center justify-center shrink-0">
            <svg class="w-5 h-5 text-violet-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 010 5.656l-3 3a4 4 0 01-5.656-5.656l1.5-1.5M10.172 13.828a4 4 0 010-5.656l3-3a4 4 0 015.656 5.656l-1.5 1.5"/></svg>
          </div>
          <div class="flex-1">
            <h3 class="text-base font-semibold text-foreground">Link de conexão</h3>
            <p v-if="nome" class="text-xs text-muted-foreground truncate">{{ nome }}</p>
          </div>
          <button @click="fechar" class="text-muted-foreground hover:text-foreground transition shrink-0">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>

        <div class="p-5 space-y-3">
          <p class="text-xs text-muted-foreground leading-snug">
            Envie este link para o profissional. Ele abre no celular dele e conecta o próprio WhatsApp (QR Code ou código de pareamento), sem precisar logar no painel.
          </p>

          <div v-if="carregando" class="flex items-center justify-center py-4 text-muted-foreground text-sm gap-2">
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
              <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
            </svg>
            Gerando link...
          </div>

          <p v-else-if="erro" class="text-xs text-red-500">{{ erro }}</p>

          <template v-else-if="url">
            <div class="flex items-center gap-2">
              <input
                :value="url"
                readonly
                @click="($event.target as HTMLInputElement).select()"
                class="flex-1 min-w-0 px-3 py-2 rounded-lg border border-border bg-muted/30 text-foreground text-xs font-mono truncate focus:outline-none"
              />
              <button
                @click="copiar"
                class="shrink-0 px-3 py-2 bg-primary text-primary-foreground rounded-lg text-xs font-medium hover:opacity-90 transition flex items-center gap-1.5"
              >
                <svg v-if="!copiado" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                {{ copiado ? 'Copiado' : 'Copiar' }}
              </button>
            </div>

            <button
              @click="revogar"
              :disabled="revogando"
              class="text-xs text-red-500 hover:text-red-600 transition disabled:opacity-50"
            >
              {{ revogando ? 'Revogando...' : 'Revogar link e gerar outro' }}
            </button>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>
