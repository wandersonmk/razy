<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

definePageMeta({ layout: 'auth' })

const QR_TTL_SECONDS = 90

const route = useRoute()
const token = String(route.params.token || '')

type Etapa = 'carregando' | 'invalido' | 'ja_conectado' | 'qr' | 'conectado' | 'erro'

const etapa = ref<Etapa>('carregando')
const nomeInstancia = ref<string>('')
const telefone = ref<string | null>(null)
const qrCode = ref<string | null>(null)
const paircode = ref<string | null>(null)
const erro = ref<string | null>(null)
const restante = ref(QR_TTL_SECONDS)
const expirado = ref(false)
const gerandoQr = ref(false)

let pollInterval: ReturnType<typeof setInterval> | null = null
let countdownInterval: ReturnType<typeof setInterval> | null = null

const qrCodeSrc = computed(() => {
  if (!qrCode.value) return null
  if (qrCode.value.startsWith('data:') || qrCode.value.startsWith('http')) return qrCode.value
  return `data:image/png;base64,${qrCode.value}`
})

const tempoFormatado = computed(() => {
  const m = Math.floor(restante.value / 60)
  const s = restante.value % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

function pararTudo() {
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
  if (countdownInterval) { clearInterval(countdownInterval); countdownInterval = null }
}

function iniciarCountdown() {
  if (countdownInterval) clearInterval(countdownInterval)
  restante.value = QR_TTL_SECONDS
  expirado.value = false
  countdownInterval = setInterval(() => {
    restante.value--
    if (restante.value <= 0) {
      pararTudo()
      expirado.value = true
    }
  }, 1000)
}

async function gerarQrCode() {
  gerandoQr.value = true
  erro.value = null
  qrCode.value = null
  paircode.value = null
  try {
    const res = await fetch(`/api/publico/conectar/${token}/connect`, { method: 'POST' })
    const data = await res.json()
    if (!res.ok) {
      erro.value = data?.statusMessage || data?.message || 'Erro ao gerar o QR Code'
      etapa.value = 'erro'
      return
    }
    if (data.connected) {
      telefone.value = data.phone || telefone.value
      etapa.value = 'conectado'
      pararTudo()
      return
    }
    qrCode.value = data.qrcode
    paircode.value = data.paircode || null
    etapa.value = 'qr'
    iniciarCountdown()

    pollInterval = setInterval(async () => {
      try {
        const r = await fetch(`/api/publico/conectar/${token}/poll`)
        const d = await r.json()
        if (d.status === 'connected') {
          telefone.value = d.phone || telefone.value
          etapa.value = 'conectado'
          pararTudo()
        }
      } catch {
        // tenta de novo no próximo tick
      }
    }, 3000)
  } catch (e: any) {
    erro.value = e?.message || 'Erro ao gerar o QR Code'
    etapa.value = 'erro'
  } finally {
    gerandoQr.value = false
  }
}

async function iniciar() {
  try {
    const res = await fetch(`/api/publico/conectar/${token}/status`)
    if (!res.ok) {
      etapa.value = 'invalido'
      return
    }
    const data = await res.json()
    nomeInstancia.value = data.nome_instancia || ''
    telefone.value = data.phone || null

    if (data.status === 'connected') {
      etapa.value = 'ja_conectado'
      return
    }
    await gerarQrCode()
  } catch {
    etapa.value = 'invalido'
  }
}

onMounted(iniciar)
onUnmounted(pararTudo)
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-sm bg-card border border-border rounded-2xl shadow-2xl overflow-hidden">
      <!-- Header -->
      <div class="relative px-5 pt-5 pb-4 border-b border-border bg-gradient-to-br from-green-500/5 via-transparent to-transparent text-center">
        <div class="w-12 h-12 mx-auto bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center shadow shadow-green-500/30 mb-2">
          <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654z"/>
          </svg>
        </div>
        <h1 class="text-base font-semibold text-foreground">Conectar WhatsApp</h1>
        <p v-if="nomeInstancia" class="text-xs text-muted-foreground mt-0.5">{{ nomeInstancia }}</p>
      </div>

      <div class="px-5 py-5">
        <!-- Carregando -->
        <div v-if="etapa === 'carregando'" class="flex flex-col items-center gap-3 py-8 text-muted-foreground">
          <svg class="w-8 h-8 animate-spin text-green-500" fill="none" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
            <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
          </svg>
          <p class="text-sm">Carregando…</p>
        </div>

        <!-- Link inválido / revogado -->
        <div v-else-if="etapa === 'invalido'" class="flex flex-col items-center gap-3 py-6 text-center">
          <div class="w-14 h-14 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
            <svg class="w-7 h-7 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          </div>
          <p class="text-sm font-medium text-foreground">Este link não é válido</p>
          <p class="text-xs text-muted-foreground">Ele pode ter sido revogado. Peça um link novo pra quem te enviou.</p>
        </div>

        <!-- Já conectado (não precisa fazer nada) -->
        <div v-else-if="etapa === 'ja_conectado' || etapa === 'conectado'" class="flex flex-col items-center gap-3 py-6 text-center">
          <div class="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/20 flex items-center justify-center animate-in zoom-in">
            <svg class="w-9 h-9 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>
          </div>
          <p class="text-base font-semibold text-green-600">
            {{ etapa === 'conectado' ? 'Conectado com sucesso!' : 'Este número já está conectado' }}
          </p>
          <p v-if="telefone" class="text-xs text-muted-foreground">{{ telefone }}</p>
          <p class="text-xs text-muted-foreground">Pode fechar esta página.</p>
        </div>

        <!-- Erro -->
        <div v-else-if="etapa === 'erro'" class="flex flex-col items-center gap-3 py-6 text-center">
          <svg class="w-10 h-10 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          <p class="text-sm text-red-500">{{ erro }}</p>
          <button @click="gerarQrCode" class="px-4 py-2 bg-primary text-primary-foreground text-sm rounded-lg hover:opacity-90">
            Tentar novamente
          </button>
        </div>

        <!-- QR Code -->
        <div v-else-if="etapa === 'qr'" class="space-y-3">
          <p class="text-xs text-muted-foreground text-center leading-snug">
            No WhatsApp: <span class="text-foreground font-medium">⋮ → Aparelhos Conectados → Conectar aparelho</span>
          </p>

          <div class="relative">
            <div class="aspect-square bg-white rounded-xl border-2 border-border flex items-center justify-center overflow-hidden p-3 shadow-inner">
              <div v-if="gerandoQr" class="flex flex-col items-center gap-3 text-muted-foreground">
                <svg class="w-10 h-10 animate-spin text-green-500" fill="none" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
                  <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
                </svg>
                <p class="text-sm font-medium text-gray-700">Gerando QR Code...</p>
              </div>
              <div v-else-if="expirado" class="flex flex-col items-center gap-3 text-center px-4">
                <div class="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center">
                  <svg class="w-8 h-8 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                </div>
                <p class="text-sm font-medium text-gray-700">QR Code expirado</p>
              </div>
              <img v-else-if="qrCodeSrc" :src="qrCodeSrc" alt="QR Code" class="w-full h-full object-contain" />
              <div v-else class="text-center text-gray-400 text-sm">Aguardando...</div>
            </div>

            <div
              v-if="qrCodeSrc && !expirado"
              class="absolute -top-2 -right-2 bg-card border border-border rounded-full px-3 py-1.5 shadow-md flex items-center gap-2"
            >
              <svg class="w-4 h-4" :class="restante > 30 ? 'text-green-500' : restante > 10 ? 'text-amber-500' : 'text-red-500'" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              <span class="text-xs font-mono font-semibold tabular-nums" :class="restante > 30 ? 'text-green-500' : restante > 10 ? 'text-amber-500' : 'text-red-500'">{{ tempoFormatado }}</span>
            </div>
          </div>

          <div v-if="paircode && !expirado" class="text-center bg-muted/30 rounded-lg py-2 px-3">
            <p class="text-[10px] text-muted-foreground mb-0.5 uppercase tracking-wide">Ou digite este código no WhatsApp</p>
            <p class="text-base font-mono font-bold tracking-widest text-foreground">{{ paircode }}</p>
          </div>

          <button
            @click="gerarQrCode"
            :disabled="gerandoQr"
            class="w-full px-3 py-2 bg-gradient-to-br from-green-500 to-green-600 text-white rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50 flex items-center justify-center gap-2 shadow shadow-green-500/20"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            {{ expirado ? 'Gerar novo QR Code' : 'Recarregar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
