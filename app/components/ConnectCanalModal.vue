<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useCanais, type Canal } from '~/composables/useCanais'

const props = defineProps<{ show: boolean; canal: Canal | null }>()
const emit = defineEmits<{ close: []; connected: [canal: Canal] }>()

const { conectar, buscarStatus } = useCanais()

const QR_TTL_SECONDS = 90

const carregando = ref(false)
const qrCode = ref<string | null>(null)
const paircode = ref<string | null>(null)
const statusAtual = ref<Canal['status']>('aguardando_qr')
const erro = ref<string | null>(null)
const expirado = ref(false)
const restante = ref(QR_TTL_SECONDS)

let pollInterval: ReturnType<typeof setInterval> | null = null
let countdownInterval: ReturnType<typeof setInterval> | null = null
let toast: any
onMounted(async () => { toast = await useToastSafe() })

const qrCodeSrc = computed(() => {
  if (!qrCode.value) return null
  if (qrCode.value.startsWith('data:')) return qrCode.value
  if (qrCode.value.startsWith('http')) return qrCode.value
  return `data:image/png;base64,${qrCode.value}`
})

const tempoFormatado = computed(() => {
  const m = Math.floor(restante.value / 60)
  const s = restante.value % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

const progressoTimer = computed(() => (restante.value / QR_TTL_SECONDS) * 100)

const timerColor = computed(() => {
  if (restante.value > 30) return 'text-green-500'
  if (restante.value > 10) return 'text-amber-500'
  return 'text-red-500'
})

function pararPolling() {
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
}

function pararCountdown() {
  if (countdownInterval) { clearInterval(countdownInterval); countdownInterval = null }
}

function pararTudo() {
  pararPolling()
  pararCountdown()
}

function fechar() {
  pararTudo()
  qrCode.value = null
  paircode.value = null
  statusAtual.value = 'aguardando_qr'
  erro.value = null
  expirado.value = false
  restante.value = QR_TTL_SECONDS
  emit('close')
}

function iniciarCountdown() {
  pararCountdown()
  restante.value = QR_TTL_SECONDS
  countdownInterval = setInterval(() => {
    restante.value--
    if (restante.value <= 0) {
      pararTudo()
      expirado.value = true
      setTimeout(() => fechar(), 1500)
    }
  }, 1000)
}

async function iniciarConexao() {
  if (!props.canal) return
  pararTudo()
  carregando.value = true
  erro.value = null
  qrCode.value = null
  paircode.value = null
  expirado.value = false
  statusAtual.value = 'aguardando_qr'
  restante.value = QR_TTL_SECONDS

  try {
    const result = await conectar(props.canal.id)
    if (result.erro) {
      erro.value = result.erro
      return
    }
    qrCode.value = result.qrcode
    paircode.value = result.paircode || null
    statusAtual.value = result.status

    if (result.connected) {
      statusAtual.value = 'conectado'
      toast?.success('Número conectado!')
      emit('connected', props.canal)
      setTimeout(fechar, 800)
      return
    }

    iniciarCountdown()

    pollInterval = setInterval(async () => {
      if (!props.canal) return
      const s = await buscarStatus(props.canal.id)
      statusAtual.value = s.status
      if (s.status === 'conectado') {
        pararTudo()
        toast?.success('Número conectado!')
        emit('connected', { ...props.canal!, ...s } as Canal)
        setTimeout(fechar, 800)
      }
    }, 3000)
  } catch (err: any) {
    erro.value = err.message || 'Erro ao conectar'
  } finally {
    carregando.value = false
  }
}

watch(() => props.show, (val) => {
  if (val && props.canal) iniciarConexao()
  else pararTudo()
})

onUnmounted(() => pararTudo())
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="show && canal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
        @click.self="fechar"
      >
        <div class="bg-card border border-border rounded-2xl w-full max-w-sm shadow-2xl overflow-hidden">
          <!-- Header -->
          <div class="relative px-5 pt-4 pb-3 border-b border-border bg-gradient-to-br from-green-500/5 via-transparent to-transparent">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center shrink-0 shadow shadow-green-500/30">
                <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654z"/>
                </svg>
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="text-base font-semibold text-foreground leading-tight">Conectar WhatsApp</h3>
                <p class="text-xs text-muted-foreground truncate">{{ canal.nome }}</p>
              </div>
              <button @click="fechar" class="text-muted-foreground hover:text-foreground transition shrink-0 -m-1 p-1 rounded-lg hover:bg-muted">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>

          <div class="px-5 py-4 space-y-3">
            <!-- Instruções compactas -->
            <p class="text-xs text-muted-foreground leading-snug">
              No WhatsApp: <span class="text-foreground font-medium">⋮ → Aparelhos Conectados → Conectar aparelho</span>
            </p>

            <!-- QR Code -->
            <div class="relative">
              <div class="aspect-square bg-white rounded-xl border-2 border-border flex items-center justify-center overflow-hidden p-3 shadow-inner">
                <!-- Loading -->
                <div v-if="carregando" class="flex flex-col items-center gap-3 text-muted-foreground">
                  <svg class="w-10 h-10 animate-spin text-green-500" fill="none" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
                    <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
                  </svg>
                  <p class="text-sm font-medium text-gray-700">Gerando QR Code...</p>
                </div>

                <!-- Conectado -->
                <div v-else-if="statusAtual === 'conectado'" class="flex flex-col items-center gap-3">
                  <div class="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center animate-in zoom-in">
                    <svg class="w-12 h-12 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
                    </svg>
                  </div>
                  <p class="text-base font-semibold text-green-600">Conectado!</p>
                </div>

                <!-- Expirado -->
                <div v-else-if="expirado" class="flex flex-col items-center gap-3 text-center px-4">
                  <div class="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center">
                    <svg class="w-8 h-8 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  </div>
                  <p class="text-sm font-medium text-gray-700">QR Code expirado</p>
                </div>

                <!-- Erro -->
                <div v-else-if="erro" class="text-center text-red-500 text-sm px-4">
                  <svg class="w-10 h-10 mx-auto mb-2 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  </svg>
                  {{ erro }}
                  <button @click="iniciarConexao" class="block mt-3 px-3 py-1.5 bg-primary text-primary-foreground text-xs rounded-lg hover:opacity-90 mx-auto">
                    Tentar novamente
                  </button>
                </div>

                <!-- QR -->
                <img v-else-if="qrCodeSrc" :src="qrCodeSrc" alt="QR Code" class="w-full h-full object-contain" />

                <div v-else class="text-center text-gray-400 text-sm">
                  Aguardando...
                </div>
              </div>

              <!-- Timer badge sobre o QR -->
              <div
                v-if="qrCodeSrc && !expirado && statusAtual !== 'conectado'"
                class="absolute -top-2 -right-2 bg-card border border-border rounded-full px-3 py-1.5 shadow-md flex items-center gap-2"
              >
                <svg :class="timerColor" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span :class="timerColor" class="text-xs font-mono font-semibold tabular-nums">{{ tempoFormatado }}</span>
              </div>
            </div>

            <!-- Barra de progresso do timer -->
            <div v-if="qrCodeSrc && !expirado && statusAtual !== 'conectado'" class="h-1 bg-muted rounded-full overflow-hidden">
              <div
                class="h-full transition-all duration-1000 ease-linear"
                :class="restante > 30 ? 'bg-green-500' : restante > 10 ? 'bg-amber-500' : 'bg-red-500'"
                :style="{ width: progressoTimer + '%' }"
              />
            </div>

            <!-- Pair code -->
            <div v-if="paircode && !expirado && statusAtual !== 'conectado'" class="text-center bg-muted/30 rounded-lg py-2 px-3">
              <p class="text-[10px] text-muted-foreground mb-0.5 uppercase tracking-wide">Código de pareamento</p>
              <p class="text-base font-mono font-bold tracking-widest text-foreground">{{ paircode }}</p>
            </div>

            <!-- Status -->
            <div
              v-if="!expirado"
              :class="statusAtual === 'conectado'
                ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800'
                : 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800'"
              class="flex items-center gap-2 px-3 py-2 rounded-lg border text-xs"
            >
              <span :class="statusAtual === 'conectado' ? 'bg-green-500' : 'bg-amber-500'" class="w-1.5 h-1.5 rounded-full animate-pulse shrink-0" />
              <span v-if="statusAtual === 'conectado'" class="font-medium">Canal conectado com sucesso!</span>
              <span v-else>Aguardando leitura do QR code...</span>
            </div>

            <div
              v-else
              class="flex items-center gap-2 px-3 py-2 rounded-lg border bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800 text-xs"
            >
              <svg class="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span>QR expirou. Fechando...</span>
            </div>
          </div>

          <div class="flex gap-2 px-5 py-3 border-t border-border bg-muted/20">
            <button
              @click="fechar"
              class="flex-1 px-3 py-2 border border-border bg-card rounded-lg text-sm font-medium text-foreground hover:bg-muted transition"
            >
              Fechar
            </button>
            <button
              @click="iniciarConexao"
              :disabled="carregando"
              class="flex-1 px-3 py-2 bg-gradient-to-br from-green-500 to-green-600 text-white rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50 flex items-center justify-center gap-2 shadow shadow-green-500/20"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              Recarregar
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-active > div,
.modal-fade-leave-active > div {
  transition: transform 0.2s ease;
}
.modal-fade-enter-from > div,
.modal-fade-leave-to > div {
  transform: scale(0.95);
}
</style>
