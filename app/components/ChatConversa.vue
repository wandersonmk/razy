<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useConversas, type Conversa, type Mensagem } from '~/composables/useConversas'

const props = defineProps<{ conversa: Conversa }>()
const emit = defineEmits<{ 'abrir-detalhes': []; 'atualizado': [] }>()

const { fetchMensagens, buscarMidiaMensagem } = useConversas()

// Tipos que podem ter arquivo anexado — só pra esses vale a pena buscar a
// mídia que faltou no broadcast (texto/reação não têm midias_conversas).
const KINDS_COM_MIDIA = new Set(['audio', 'image', 'sticker', 'document', 'video'])

const mensagens = ref<Mensagem[]>([])
const carregando = ref(false)
const carregandoMais = ref(false)
const temMais = ref(true)
const scrollBox = ref<HTMLElement | null>(null)

async function carregarInicial() {
  const idConversaAlvo = props.conversa.id
  carregando.value = true
  mensagens.value = []
  temMais.value = true
  try {
    const dados = await fetchMensagens(idConversaAlvo, { limit: 40 })
    // Corrida: o usuário já trocou de conversa de novo enquanto o fetch
    // estava em voo — essa resposta é velha, não sobrescreve o que já está
    // carregando pra conversa atual.
    if (idConversaAlvo !== props.conversa.id) return
    // Mensagem que chegou via Realtime enquanto o fetch estava em voo (o
    // fetch pode rodar antes do commit no banco) — preserva e mescla por
    // data em vez de sobrescrever e perder a mensagem que acabou de chegar.
    const chegadasDuranteFetch = mensagens.value.filter((m) => !dados.some((d) => d.id === m.id))
    mensagens.value = chegadasDuranteFetch.length
      ? [...dados, ...chegadasDuranteFetch].sort((a, b) => new Date(a.data_hora).getTime() - new Date(b.data_hora).getTime())
      : dados
    if (dados.length < 40) temMais.value = false
    await nextTick()
    irParaFinal()
  } finally {
    carregando.value = false
  }
}

async function carregarMaisAntigas() {
  if (!mensagens.value.length || carregandoMais.value) return
  const idConversaAlvo = props.conversa.id
  carregandoMais.value = true
  try {
    const primeira = mensagens.value[0]
    const antigas = await fetchMensagens(idConversaAlvo, { before: primeira.data_hora, beforeId: primeira.id, limit: 40 })
    // Trocou de conversa enquanto carregava — descarta, senão mensagem
    // antiga da conversa errada entra na tela.
    if (idConversaAlvo !== props.conversa.id) return
    if (antigas.length < 40) temMais.value = false
    const novas = antigas.filter((m) => !mensagens.value.some((existente) => existente.id === m.id))
    if (novas.length) {
      const alturaAntes = scrollBox.value?.scrollHeight || 0
      mensagens.value = [...novas, ...mensagens.value]
      await nextTick()
      if (scrollBox.value) {
        scrollBox.value.scrollTop = scrollBox.value.scrollHeight - alturaAntes
      }
    }
  } finally {
    carregandoMais.value = false
  }
}

// Margem para considerar "está no fim". Não é zero porque a rolagem raramente
// para no pixel exato — e porque quem está a duas linhas do fim ainda está
// acompanhando a conversa ao vivo.
const MARGEM_FIM = 120
const noFim = ref(true)

function estaNoFim(): boolean {
  const el = scrollBox.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight <= MARGEM_FIM
}

function atualizarNoFim() {
  noFim.value = estaNoFim()
}

/** Rolagem suave só quando o usuário pediu — e nunca se ele desativou animações. */
function irParaFinal(suave = false) {
  const el = scrollBox.value
  if (!el) return
  const reduzir = typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  el.scrollTo({ top: el.scrollHeight, behavior: suave && !reduzir ? 'smooth' : 'auto' })
  noFim.value = true
}

function onScroll() {
  atualizarNoFim()
  if (scrollBox.value && scrollBox.value.scrollTop < 60 && temMais.value && !carregandoMais.value) {
    carregarMaisAntigas()
  }
}

watch(() => props.conversa.id, () => { noFim.value = true; carregarInicial() })
onMounted(carregarInicial)

// Imagem e áudio só ganham altura depois de carregar, muito depois do
// `irParaFinal()` da carga inicial. Sem reancorar, abrir uma conversa cheia de
// mídia deixa a rolagem parada no meio — o "fim" de quando a conta foi feita.
// Só reancora enquanto o usuário está no fim: se ele subiu para ler, mexer na
// rolagem dele seria pior do que o desalinhamento.
const conteudo = ref<HTMLElement | null>(null)
let observador: ResizeObserver | null = null

onMounted(() => {
  if (typeof ResizeObserver === 'undefined' || !conteudo.value) return
  observador = new ResizeObserver(() => { if (noFim.value) irParaFinal() })
  observador.observe(conteudo.value)
})
onUnmounted(() => { observador?.disconnect(); observador = null })

// Adiciona uma mensagem chegada via tempo real (chamado pelo pai).
function adicionarMensagemRealtime(msg: Mensagem) {
  if (msg.conversa_id !== props.conversa.id) return
  if (mensagens.value.some((m) => m.id === msg.id)) return
  // Decidido ANTES de inserir: depois da inserção a altura já cresceu e a conta
  // diria que o usuário saiu do fim. Se ele subiu para ler o histórico, mensagem
  // nova não pode arrancá-lo de volta — só acende a seta.
  const acompanhando = estaNoFim()
  mensagens.value = [...mensagens.value, msg]
  nextTick(() => (acompanhando ? irParaFinal(true) : atualizarNoFim()))

  // O broadcast manda a linha crua de `mensagens` — sem o embed de
  // midias_conversas. Se for um tipo com arquivo, busca à parte e completa a
  // mensagem já em tela (MensagemBolha reage sozinha, via watch).
  if (msg.kind && KINDS_COM_MIDIA.has(msg.kind) && !msg.midia) {
    buscarMidiaMensagem(msg.id).then((midia) => {
      if (!midia) return
      const alvo = mensagens.value.find((m) => m.id === msg.id)
      if (alvo) alvo.midia = midia
    })
  }
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
    <!-- `relative` aqui e não no scrollBox: a seta precisa ficar parada sobre a
         lista, e dentro do container que rola ela subiria junto com o conteúdo. -->
    <div class="relative flex-1 min-h-0">
      <div ref="scrollBox" @scroll="onScroll" class="h-full overflow-y-auto">
        <div ref="conteudo" class="px-4 py-4 space-y-2.5">
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

      <!-- Voltar ao fim.
           `bottom-24` empilha a seta ACIMA do botão flutuante do Analista
           (fixed bottom-6, 56px de altura), que ocupa até 80px da borda. As duas
           ficam na mesma calha da direita, o que parece intencional em vez de
           acidental. -->
      <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-1 scale-95"
        leave-active-class="transition duration-150 ease-in"
        leave-to-class="opacity-0 translate-y-1 scale-95"
      >
        <button
          v-if="!noFim && !carregando && mensagens.length"
          @click="irParaFinal(true)"
          type="button"
          aria-label="Ir para a mensagem mais recente"
          title="Ir para a mensagem mais recente"
          class="absolute bottom-24 right-6 z-20 w-10 h-10 rounded-full bg-card border border-border text-muted-foreground shadow-lg hover:text-foreground hover:border-primary/50 hover:-translate-y-0.5 transition focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background"
        >
          <svg class="w-5 h-5 mx-auto" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 5v14M19 12l-7 7-7-7" />
          </svg>
        </button>
      </Transition>
    </div>
  </div>
</template>
