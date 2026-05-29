<script setup lang="ts">
import { ref } from 'vue'
import { useCanais, type Canal } from '~/composables/useCanais'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: []; created: [canal: Canal] }>()

const { criarCanal } = useCanais()

type Step = 'tipo' | 'nome'
const step = ref<Step>('tipo')
const tipoSelecionado = ref<Canal['tipo']>('nativo')
const nome = ref('')
const criando = ref(false)

let toast: any
onMounted(async () => { toast = await useToastSafe() })

const tipos = [
  {
    id: 'nativo' as const,
    nome: 'Criar canal Nativo',
    descricao: 'Conexão nativa, estável e rápida via QR Code',
    icone: 'whatsapp',
    cor: 'bg-green-500',
    disponivel: true
  }
]

function reset() {
  step.value = 'tipo'
  tipoSelecionado.value = 'nativo'
  nome.value = ''
  criando.value = false
}

function fechar() {
  reset()
  emit('close')
}

function escolherTipo(tipo: typeof tipos[number]) {
  if (!tipo.disponivel) return
  tipoSelecionado.value = tipo.id
  step.value = 'nome'
}

async function confirmarCriar() {
  if (!nome.value.trim()) { toast?.warning('Informe o nome'); return }

  criando.value = true
  try {
    const canal = await criarCanal(nome.value.trim(), tipoSelecionado.value)
    toast?.success('Canal criado! Clique em "Conectar" no card para gerar o QR Code.')
    emit('created', canal)
    fechar()
  } catch (err: any) {
    toast?.error(err.message || 'Erro ao criar canal')
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
        <!-- ── Step 1: Escolher tipo ────────────────────────────────── -->
        <template v-if="step === 'tipo'">
          <div class="flex items-start gap-3 p-6 border-b border-border">
            <div class="w-12 h-12 bg-foreground/10 rounded-xl flex items-center justify-center shrink-0">
              <svg class="w-6 h-6 text-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-foreground">Adicionar Canal</h3>
              <p class="text-sm text-muted-foreground">Escolha o tipo de canal que deseja conectar</p>
            </div>
            <button @click="fechar" class="text-muted-foreground hover:text-foreground transition shrink-0">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="p-4 space-y-2">
            <button
              v-for="t in tipos"
              :key="t.id"
              @click="escolherTipo(t)"
              :disabled="!t.disponivel"
              class="w-full flex items-center gap-3 p-3 border border-border rounded-xl text-left transition hover:border-primary/50 hover:bg-muted/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-border disabled:hover:bg-transparent"
            >
              <div :class="[t.cor, 'w-12 h-12 rounded-xl flex items-center justify-center shrink-0']">
                <svg v-if="t.icone === 'whatsapp'" class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654z"/>
                </svg>
                <svg v-else-if="t.icone === 'meta'" class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892z"/>
                </svg>
                <svg v-else class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-4 0v7h-4v-7a6 6 0 016-6z"/>
                </svg>
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <p class="font-medium text-foreground">{{ t.nome }}</p>
                  <span v-if="t.badge" class="text-[10px] px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded font-semibold">{{ t.badge }}</span>
                </div>
                <p class="text-xs text-muted-foreground">{{ t.descricao }}</p>
              </div>
              <svg v-if="t.disponivel" class="w-5 h-5 text-muted-foreground shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </button>
          </div>

          <div class="p-4 border-t border-border text-xs text-muted-foreground flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
            </svg>
            Conexão segura e criptografada
          </div>
        </template>

        <!-- ── Step 2: Nome do canal ────────────────────────────────── -->
        <template v-else-if="step === 'nome'">
          <div class="flex items-start gap-3 p-6 border-b border-border">
            <div class="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center shrink-0">
              <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654z"/>
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-foreground">Nova Conexão</h3>
              <p class="text-sm text-muted-foreground">WhatsApp QRCode</p>
            </div>
            <button @click="fechar" class="text-muted-foreground hover:text-foreground transition shrink-0">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="p-6 space-y-4">
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Nome do Canal</label>
              <div class="relative">
                <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/>
                </svg>
                <input
                  v-model="nome"
                  type="text"
                  placeholder="Ex: Atendimento Principal"
                  class="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            </div>

          </div>

          <div class="flex gap-3 p-4 border-t border-border">
            <button @click="step = 'tipo'" class="flex-1 px-4 py-2 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-muted transition">
              Voltar
            </button>
            <button
              @click="confirmarCriar"
              :disabled="criando || !nome"
              class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50"
            >
              {{ criando ? 'Criando...' : 'Criar Canal' }}
            </button>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>
