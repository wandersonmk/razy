<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useConversas, type Conversa, type Mensagem } from '~/composables/useConversas'

const props = defineProps<{ conversa: Conversa }>()
const emit = defineEmits<{ 'abrir-detalhes': []; 'atualizado': [] }>()

const { fetchMensagens } = useConversas()

const mensagens = ref<Mensagem[]>([])
const carregando = ref(false)
const carregandoMais = ref(false)
const temMais = ref(true)
const scrollBox = ref<HTMLElement | null>(null)

async function carregarInicial() {
  carregando.value = true
  mensagens.value = []
  temMais.value = true
  try {
    const dados = await fetchMensagens(props.conversa.id, { limit: 40 })
    mensagens.value = dados
    if (dados.length < 40) temMais.value = false
    await nextTick()
    irParaFinal()
  } finally {
    carregando.value = false
  }
}

async function carregarMaisAntigas() {
  if (!mensagens.value.length || carregandoMais.value) return
  carregandoMais.value = true
  try {
    const primeira = mensagens.value[0]
    const antigas = await fetchMensagens(props.conversa.id, { before: primeira.data_hora, limit: 40 })
    if (antigas.length < 40) temMais.value = false
    if (antigas.length) {
      const alturaAntes = scrollBox.value?.scrollHeight || 0
      mensagens.value = [...antigas, ...mensagens.value]
      await nextTick()
      if (scrollBox.value) {
        scrollBox.value.scrollTop = scrollBox.value.scrollHeight - alturaAntes
      }
    }
  } finally {
    carregandoMais.value = false
  }
}

function irParaFinal() {
  if (scrollBox.value) scrollBox.value.scrollTop = scrollBox.value.scrollHeight
}

function onScroll() {
  if (scrollBox.value && scrollBox.value.scrollTop < 60 && temMais.value && !carregandoMais.value) {
    carregarMaisAntigas()
  }
}

watch(() => props.conversa.id, () => { carregarInicial() })
onMounted(carregarInicial)

// Adiciona uma mensagem chegada via tempo real (chamado pelo pai).
function adicionarMensagemRealtime(msg: Mensagem) {
  if (msg.conversa_id !== props.conversa.id) return
  if (mensagens.value.some((m) => m.id === msg.id)) return
  mensagens.value = [...mensagens.value, msg]
  nextTick(irParaFinal)
}

defineExpose({ adicionarMensagemRealtime })

// ── Badges de status (relógio ao vivo) ──────────────────────────────────────
const agora = ref(Date.now())
let tick: ReturnType<typeof setInterval> | null = null
onMounted(() => { tick = setInterval(() => { agora.value = Date.now() }, 1000) })
onUnmounted(() => { if (tick) clearInterval(tick) })

function formatarDuracao(ms: number): string {
  const totalSeg = Math.max(0, Math.floor(ms / 1000))
  const h = Math.floor(totalSeg / 3600)
  const m = Math.floor((totalSeg % 3600) / 60)
  const s = totalSeg % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

const pausaRestanteMs = computed(() => {
  const c = props.conversa
  if (!c.tempo_pausa || !c.tempo_pausa_inicio) return 0
  const fim = new Date(c.tempo_pausa_inicio).getTime() + c.tempo_pausa * 1000
  return fim - agora.value
})
const estaPausado = computed(() => pausaRestanteMs.value > 0)
const pausaPermanente = computed(() => (props.conversa.tempo_pausa || 0) >= 60 * 60 * 24 * 300)

const atendimentoAberto = computed(() => !!props.conversa.opened_at && !props.conversa.closed_at)
const atendimentoFechado = computed(() => !!props.conversa.closed_at)

// Tempo até a 1ª resposta: entre a 1ª mensagem do cliente e a 1ª resposta
// (profissional pelo celular ou IA) — é a métrica que faz sentido aqui, porque
// é 100% automática. "Tempo de atendimento" (aberto → fechado) depende de
// alguém clicar em "Fechar" no painel, o que não tem como acontecer sozinho
// já que o profissional atende pelo próprio celular, sem usar o app.
const tempoPrimeiraRespostaSeg = computed(() => {
  const primeiraRecebida = mensagens.value.find((m) => m.direcao === 'RECEIVED')
  if (!primeiraRecebida) return null
  const primeiraResposta = mensagens.value.find(
    (m) => m.direcao === 'SENT' && new Date(m.data_hora).getTime() > new Date(primeiraRecebida.data_hora).getTime()
  )
  if (!primeiraResposta) return null
  return Math.max(0, Math.round((new Date(primeiraResposta.data_hora).getTime() - new Date(primeiraRecebida.data_hora).getTime()) / 1000))
})
const aguardandoPrimeiraResposta = computed(() =>
  tempoPrimeiraRespostaSeg.value === null && mensagens.value.some((m) => m.direcao === 'RECEIVED')
)

function formatTelefone(tel: string): string {
  const n = (tel || '').replace(/\D/g, '')
  if (n.length === 13) return `+${n.slice(0, 2)} ${n.slice(2, 4)} ${n.slice(4, 9)}-${n.slice(9)}`
  if (n.length === 12) return `+${n.slice(0, 2)} ${n.slice(2, 4)} ${n.slice(4, 8)}-${n.slice(8)}`
  return tel
}
</script>

<template>
  <div class="flex flex-col h-full bg-background">
    <!-- Header -->
    <div class="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0">
      <AvatarContato :nome="conversa.nome_contato" :numero="conversa.numero" :photo="conversa.photo" size-class="w-10 h-10 text-sm" />
      <div class="min-w-0 flex-1">
        <p class="font-semibold text-foreground truncate">{{ conversa.nome_contato || formatTelefone(conversa.numero) }}</p>
        <p class="text-xs text-muted-foreground truncate">
          <span v-if="conversa.profissional?.nome" class="text-foreground/80 font-medium">{{ conversa.profissional.nome }}</span>
          <span v-if="conversa.profissional?.nome"> · </span>
          {{ formatTelefone(conversa.numero) }}
        </p>
      </div>
      <div class="flex items-center gap-1.5 flex-wrap justify-end">
        <span v-if="estaPausado" class="text-[11px] px-2 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 font-medium whitespace-nowrap">
          ⏸ {{ pausaPermanente ? 'Pausado permanente' : `Pausado ${formatarDuracao(pausaRestanteMs)}` }}
        </span>
        <span v-if="tempoPrimeiraRespostaSeg !== null" class="text-[11px] px-2 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium whitespace-nowrap" title="Tempo entre a 1ª mensagem do cliente e a 1ª resposta">
          ⏱ Respondeu em {{ formatarDuracao(tempoPrimeiraRespostaSeg * 1000) }}
        </span>
        <span v-else-if="aguardandoPrimeiraResposta" class="text-[11px] px-2 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 font-medium whitespace-nowrap">
          ⏳ Aguardando resposta
        </span>
        <span v-if="atendimentoFechado" class="text-[11px] px-2 py-1 rounded-full bg-muted text-muted-foreground font-medium whitespace-nowrap">
          ✓ Resolvida
        </span>
        <span v-else-if="atendimentoAberto" class="text-[11px] px-2 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 font-medium whitespace-nowrap">
          🟢 Em atendimento
        </span>
        <button @click="$emit('abrir-detalhes')" class="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition" title="Detalhes">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        </button>
      </div>
    </div>

    <!-- Mensagens -->
    <div ref="scrollBox" @scroll="onScroll" class="flex-1 overflow-y-auto px-4 py-4 space-y-2.5">
      <div v-if="carregando" class="flex items-center justify-center py-10 text-sm text-muted-foreground">Carregando conversa...</div>
      <template v-else>
        <div v-if="carregandoMais" class="text-center text-xs text-muted-foreground py-1">Carregando mensagens antigas...</div>
        <div v-if="!mensagens.length" class="text-center text-sm text-muted-foreground py-10">Nenhuma mensagem ainda.</div>
        <MensagemBolha
          v-for="m in mensagens"
          :key="m.id"
          :mensagem="m"
          :nome-profissional="conversa.profissional?.nome || null"
        />
      </template>
    </div>
  </div>
</template>
