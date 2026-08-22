<script setup lang="ts">
import { ref } from 'vue'
import { useProfissionais, type Profissional } from '~/composables/useProfissionais'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: []; created: [payload: { profissional: Profissional; instancia: any }] }>()

const { criarProfissionalComCanal } = useProfissionais()

const nome = ref('')
const telefone = ref('')
const criando = ref(false)

let toast: any
onMounted(async () => { toast = await useToastSafe() })

function reset() {
  nome.value = ''
  telefone.value = ''
  criando.value = false
}

// Máscara de telefone BR (mesmo padrão usado em AssistenteManager.vue).
function maskTel(valor: string): string {
  let d = (valor || '').replace(/\D/g, '')
  if (d.length > 11 && d.startsWith('55')) d = d.slice(2)
  d = d.slice(0, 11)
  if (d.length <= 2) return d.length ? `(${d}` : ''
  if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
}

function onTelefoneInput(valor: string) {
  telefone.value = maskTel(valor)
}

function soDigitos(valor: string): string {
  return (valor || '').replace(/\D/g, '')
}

function fechar() {
  reset()
  emit('close')
}

async function confirmar() {
  if (!nome.value.trim()) { toast?.warning('Informe o nome do profissional'); return }

  criando.value = true
  try {
    const telDigitos = soDigitos(telefone.value)
    const resultado = await criarProfissionalComCanal(nome.value.trim(), telDigitos.length >= 10 ? telDigitos : undefined)
    toast?.success('Profissional cadastrado! Clique em "Conectar" para gerar o QR Code.')
    emit('created', resultado)
    fechar()
  } catch (err: any) {
    toast?.error(err.message || 'Erro ao cadastrar profissional')
  } finally {
    criando.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      @click.self="fechar"
    >
      <div class="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        <div class="flex items-start gap-3 p-6 border-b border-border">
          <div class="w-12 h-12 bg-violet-500/10 rounded-xl flex items-center justify-center shrink-0">
            <svg class="w-6 h-6 text-violet-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
            </svg>
          </div>
          <div class="flex-1">
            <h3 class="text-lg font-semibold text-foreground">Novo profissional</h3>
            <p class="text-sm text-muted-foreground">Cada profissional ganha o próprio número — ele responde pelo celular dele, o painel só acompanha.</p>
          </div>
          <button @click="fechar" class="text-muted-foreground hover:text-foreground transition shrink-0">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-foreground mb-1">Nome do profissional</label>
            <input
              v-model="nome"
              type="text"
              placeholder="Ex: João Silva"
              autofocus
              @keyup.enter="confirmar"
              class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-foreground mb-1">Telefone <span class="text-muted-foreground font-normal">(opcional)</span></label>
            <input
              :value="telefone"
              @input="onTelefoneInput(($event.target as HTMLInputElement).value)"
              type="text"
              inputmode="numeric"
              placeholder="(11) 91460-0243"
              @keyup.enter="confirmar"
              class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <p class="text-xs text-muted-foreground">
            Depois de cadastrar, você gera o QR Code para conectar o WhatsApp dele. A IA fica desligada por padrão — liga em "IA dos Profissionais" quando quiser.
          </p>
        </div>

        <div class="flex gap-3 p-4 border-t border-border">
          <button @click="fechar" class="flex-1 px-4 py-2 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-muted transition">
            Cancelar
          </button>
          <button
            @click="confirmar"
            :disabled="criando || !nome.trim()"
            class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50"
          >
            {{ criando ? 'Cadastrando...' : 'Cadastrar' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
