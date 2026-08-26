<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useConversas, type Conversa, type Mensagem } from '~/composables/useConversas'
import { useComposer } from '~/composables/useComposer'
import { useToastSafe } from '~/composables/useToastSafe'

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

// O componente NÃO é remontado ao trocar de conversa (ConversasManager.vue não
// usa :key) — sem isto, rascunho digitado, imagens pendentes e gravação em
// andamento pra conversa A vazariam pra tela da conversa B.
watch(() => props.conversa.id, () => { noFim.value = true; carregarInicial(); resetComposer() })
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

// ── Composer: o dono manda mensagem por aqui — texto, áudio, imagem, vídeo ou
// documento — a qualquer momento, mesmo com a IA ligada. Cada envio, qualquer
// que seja o tipo, pausa a IA sozinha (ver server/api/conversas/[id]/mensagens.post.ts).
// A mensagem que a API devolve entra pelo MESMO caminho de uma chegada por
// Realtime (`adicionarMensagemRealtime`, já expõe: dedupe por id, respeita se o
// usuário está lendo o histórico, e busca a mídia que a resposta não embute).
const { enviarTexto: enviarTextoApi, enviarAudio: enviarAudioApi, enviarImagemOuVideo: enviarImagemApi, enviarDocumento: enviarDocumentoApi } = useComposer(() => props.conversa.id)

let toast: any = null
onMounted(async () => { toast = await useToastSafe() })

function avisarErro(e: unknown) {
  const msg = e instanceof Error ? e.message : 'Não consegui enviar. Tente de novo.'
  if (toast?.error) toast.error(msg)
  else alert(msg)
}

const canalConectado = computed(() => props.conversa.instancia?.status === 'connected')

// Texto
const entrada = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const enviandoTexto = ref(false)

function autoResize() {
  const ta = textareaRef.value
  if (!ta) return
  ta.style.height = 'auto'
  const LINE_HEIGHT = 21
  const MAX_LINHAS = 8
  ta.style.height = Math.min(ta.scrollHeight, LINE_HEIGHT * MAX_LINHAS) + 'px'
}

function handleEnter(e: KeyboardEvent) {
  if (e.key !== 'Enter') return
  if (e.shiftKey) { nextTick(autoResize); return }
  e.preventDefault()
  enviar()
}

async function enviar() {
  if (imagensPendentes.value.length) { await enviarImagensPendentes(); return }
  const texto = entrada.value.trim()
  if (!texto || enviandoTexto.value) return
  entrada.value = ''
  nextTick(autoResize)
  enviandoTexto.value = true
  try {
    const msg = await enviarTextoApi(texto)
    adicionarMensagemRealtime(msg)
  } catch (e) {
    avisarErro(e)
    entrada.value = texto // devolve o texto: o usuário não perde o que escreveu
    nextTick(autoResize)
  } finally {
    enviandoTexto.value = false
  }
}

// ── Áudio ──
type EstadoAudio = 'idle' | 'recording' | 'recorded' | 'uploading'
const estadoAudio = ref<EstadoAudio>('idle')
const tempoGravacao = ref(0)
const audioUrl = ref<string | null>(null)
const audioBlob = ref<Blob | null>(null)
let audioExtensao = 'webm'
let mediaRecorderRef: MediaRecorder | null = null
let streamAudioAtual: MediaStream | null = null
let audioChunks: Blob[] = []
let intervaloGravacao: ReturnType<typeof setInterval> | null = null

function formatarCronometro(seg: number): string {
  const m = Math.floor(seg / 60)
  const s = seg % 60
  return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`
}

function melhorMimeTypeAudio(): { mimeType: string; extensao: string } {
  // ogg/opus primeiro: melhor compatibilidade com a Cloud API do WhatsApp,
  // evita transcodificação no servidor.
  if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/ogg; codecs=opus')) {
    return { mimeType: 'audio/ogg; codecs=opus', extensao: 'ogg' }
  }
  if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported('audio/webm; codecs=opus')) {
    return { mimeType: 'audio/webm; codecs=opus', extensao: 'webm' }
  }
  return { mimeType: 'audio/webm', extensao: 'webm' }
}

async function iniciarGravacao() {
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    avisarErro(new Error('Este navegador não permite gravar áudio.'))
    return
  }
  let stream: MediaStream
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    avisarErro(new Error('Permissão de microfone negada.'))
    return
  }
  const { mimeType, extensao } = melhorMimeTypeAudio()
  audioExtensao = extensao
  audioChunks = []
  const recorder = new MediaRecorder(stream, { mimeType })
  recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
  recorder.onstop = () => {
    audioBlob.value = new Blob(audioChunks, { type: mimeType })
    audioUrl.value = URL.createObjectURL(audioBlob.value)
    estadoAudio.value = 'recorded'
    stream.getTracks().forEach((t) => t.stop())
  }
  recorder.start()
  mediaRecorderRef = recorder
  streamAudioAtual = stream
  estadoAudio.value = 'recording'
  tempoGravacao.value = 0
  intervaloGravacao = setInterval(() => { tempoGravacao.value++ }, 1000)
}

function pararGravacao() {
  if (mediaRecorderRef?.state === 'recording') mediaRecorderRef.stop()
  if (intervaloGravacao) { clearInterval(intervaloGravacao); intervaloGravacao = null }
}

function cancelarGravacao() {
  // Desliga o onstop ANTES de parar: MediaRecorder.stop() dispara o evento de
  // forma assíncrona, então sem isto o handler registrado em iniciarGravacao()
  // roda alguns instantes depois, seta estadoAudio de volta pra 'recorded' e
  // "descancela" a gravação que acabou de ser descartada.
  if (mediaRecorderRef) { mediaRecorderRef.onstop = null; mediaRecorderRef.ondataavailable = null }
  if (mediaRecorderRef?.state === 'recording') mediaRecorderRef.stop()
  streamAudioAtual?.getTracks().forEach((t) => t.stop())
  streamAudioAtual = null
  if (intervaloGravacao) { clearInterval(intervaloGravacao); intervaloGravacao = null }
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
  audioUrl.value = null
  audioBlob.value = null
  tempoGravacao.value = 0
  estadoAudio.value = 'idle'
}

async function enviarAudioGravado() {
  if (!audioBlob.value) return
  estadoAudio.value = 'uploading'
  try {
    const msg = await enviarAudioApi(audioBlob.value, audioExtensao)
    adicionarMensagemRealtime(msg)
    cancelarGravacao()
  } catch (e) {
    avisarErro(e)
    estadoAudio.value = 'recorded' // deixa tentar de novo sem regravar
  }
}

// ── Imagem / vídeo / documento ──
const LIMITE_LOTE = 15
const imagensPendentes = ref<Array<{ file: File; previewUrl: string; video: boolean }>>([])
const enviandoLote = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const mostrarMenuAnexo = ref(false)
const anexoMenuRef = ref<HTMLElement | null>(null)
const isDraggingOver = ref(false)

// Mesmo padrão de "clique fora fecha" já usado em ConversasManager.vue
// (onClickForaFiltroPeriodo) — não existe diretiva v-click-outside neste projeto.
function onClickForaAnexoMenu(e: MouseEvent) {
  if (mostrarMenuAnexo.value && anexoMenuRef.value && !anexoMenuRef.value.contains(e.target as Node)) {
    mostrarMenuAnexo.value = false
  }
}

function abrirSeletorArquivo() {
  mostrarMenuAnexo.value = false
  fileInputRef.value?.click()
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  processarArquivos(Array.from(input.files || []))
  input.value = ''
}

function handleDrop(e: DragEvent) {
  isDraggingOver.value = false
  processarArquivos(Array.from(e.dataTransfer?.files || []))
}

function processarArquivos(files: File[]) {
  const visuais = files.filter((f) => f.type.startsWith('image/') || f.type.startsWith('video/'))
  const documentos = files.filter((f) => !f.type.startsWith('image/') && !f.type.startsWith('video/'))
  if (visuais.length) adicionarImagensPendentes(visuais)
  documentos.forEach((f) => enviarDocumentoDireto(f))
}

function adicionarImagensPendentes(files: File[]) {
  const vagas = LIMITE_LOTE - imagensPendentes.value.length
  if (vagas <= 0) { toast?.error?.(`Limite de ${LIMITE_LOTE} arquivos por vez`); return }
  files.slice(0, vagas).forEach((file) => {
    imagensPendentes.value.push({ file, previewUrl: URL.createObjectURL(file), video: file.type.startsWith('video/') })
  })
}

function removerImagemPendente(idx: number) {
  const [removida] = imagensPendentes.value.splice(idx, 1)
  if (removida) URL.revokeObjectURL(removida.previewUrl)
}

async function enviarImagensPendentes() {
  if (!imagensPendentes.value.length || enviandoLote.value) return
  enviandoLote.value = true
  const lote = imagensPendentes.value.splice(0, imagensPendentes.value.length)
  const legenda = entrada.value.trim()
  entrada.value = ''
  nextTick(autoResize)
  try {
    for (let i = 0; i < lote.length; i++) {
      const item = lote[i]
      try {
        const msg = await enviarImagemApi(item.file, i === lote.length - 1 ? (legenda || undefined) : undefined)
        adicionarMensagemRealtime(msg)
      } catch (e) {
        avisarErro(e)
      } finally {
        URL.revokeObjectURL(item.previewUrl)
      }
    }
  } finally {
    enviandoLote.value = false
  }
}

async function enviarDocumentoDireto(file: File) {
  try {
    const msg = await enviarDocumentoApi(file)
    adicionarMensagemRealtime(msg)
  } catch (e) {
    avisarErro(e)
  }
}

// Cola (Ctrl+V) uma imagem — funciona mesmo sem o textarea focado, contanto
// que o foco não esteja em outro campo (a pessoa pode estar colando pra
// responder um cliente diferente do que estava editando).
function handlePasteTextarea(e: ClipboardEvent) {
  tentarColarImagem(e)
}
function handlePasteDocumento(e: ClipboardEvent) {
  const ativo = document.activeElement as HTMLElement | null
  const focoEmCampo = ativo && (ativo.tagName === 'TEXTAREA' || ativo.tagName === 'INPUT' || ativo.isContentEditable)
  if (focoEmCampo) return
  if (estadoAudio.value !== 'idle' || mostrarCamera.value) return
  tentarColarImagem(e)
}
function tentarColarImagem(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) { e.preventDefault(); adicionarImagensPendentes([file]) }
      return
    }
  }
}

// ── Câmera ──
const mostrarCamera = ref(false)
const cameraVideoRef = ref<HTMLVideoElement | null>(null)
const cameraCanvasRef = ref<HTMLCanvasElement | null>(null)
const fotoCapturada = ref<string | null>(null)
let cameraStream: MediaStream | null = null

async function abrirCamera() {
  mostrarMenuAnexo.value = false
  mostrarCamera.value = true
  fotoCapturada.value = null
  await nextTick()
  if (!navigator.mediaDevices?.getUserMedia) {
    avisarErro(new Error('Câmera não disponível neste navegador.'))
    mostrarCamera.value = false
    return
  }
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
    if (cameraVideoRef.value) cameraVideoRef.value.srcObject = cameraStream
  } catch {
    avisarErro(new Error('Permissão de câmera negada.'))
    mostrarCamera.value = false
  }
}

function fecharCamera() {
  cameraStream?.getTracks().forEach((t) => t.stop())
  cameraStream = null
  mostrarCamera.value = false
  fotoCapturada.value = null
}

function tirarFoto() {
  const video = cameraVideoRef.value
  const canvas = cameraCanvasRef.value
  if (!video || !canvas) return
  canvas.width = video.videoWidth || 480
  canvas.height = video.videoHeight || 360
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  fotoCapturada.value = canvas.toDataURL('image/jpeg', 0.9)
  cameraStream?.getTracks().forEach((t) => t.stop())
  cameraStream = null
}

function refazerFoto() {
  fotoCapturada.value = null
  abrirCamera()
}

async function usarFoto() {
  if (!fotoCapturada.value) return
  const blob = await (await fetch(fotoCapturada.value)).blob()
  const file = new File([blob], `foto-${Date.now()}.jpg`, { type: 'image/jpeg' })
  imagensPendentes.value.push({ file, previewUrl: fotoCapturada.value, video: false })
  fecharCamera()
}

/** Encerra qualquer gravação/câmera/anexo em andamento — trocar de conversa
 * ou desmontar o componente nunca deixa stream de mic/câmera "vazando" ligado
 * (o indicador do navegador continuaria aceso) nem rascunho de uma conversa
 * aparecendo em outra. */
function resetComposer() {
  entrada.value = ''
  mostrarMenuAnexo.value = false
  isDraggingOver.value = false

  if (mediaRecorderRef?.state === 'recording') mediaRecorderRef.stop()
  streamAudioAtual?.getTracks().forEach((t) => t.stop())
  streamAudioAtual = null
  if (intervaloGravacao) { clearInterval(intervaloGravacao); intervaloGravacao = null }
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
  audioUrl.value = null
  audioBlob.value = null
  tempoGravacao.value = 0
  estadoAudio.value = 'idle'

  imagensPendentes.value.forEach((p) => URL.revokeObjectURL(p.previewUrl))
  imagensPendentes.value = []

  fecharCamera()
}

onMounted(() => {
  document.addEventListener('paste', handlePasteDocumento)
  document.addEventListener('click', onClickForaAnexoMenu)
})
onUnmounted(() => {
  document.removeEventListener('paste', handlePasteDocumento)
  document.removeEventListener('click', onClickForaAnexoMenu)
  resetComposer()
})
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

    <!-- Composer: o dono manda mensagem daqui, a qualquer momento, mesmo com a
         IA ligada — cada envio pausa a IA sozinha (ver useComposer.ts). -->
    <div class="border-t border-border shrink-0 px-3 py-2.5">
      <p v-if="!canalConectado" class="text-xs text-amber-600 dark:text-amber-400 mb-2 flex items-center gap-1.5">
        <svg class="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></svg>
        Canal desconectado — reconecte para enviar mensagens.
      </p>

      <!-- Miniaturas pendentes (imagem/vídeo) -->
      <div v-if="imagensPendentes.length" class="flex items-center gap-2 flex-wrap px-0.5 pb-2">
        <div v-for="(img, idx) in imagensPendentes" :key="img.previewUrl" class="relative shrink-0">
          <img v-if="!img.video" :src="img.previewUrl" class="h-14 w-14 object-cover rounded-lg border border-border" alt="Prévia" />
          <div v-else class="h-14 w-14 rounded-lg border border-border bg-muted grid place-items-center">
            <svg class="w-5 h-5 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z" /><rect x="1" y="5" width="15" height="14" rx="2" /></svg>
          </div>
          <button
            @click="removerImagemPendente(idx)"
            title="Remover"
            class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-destructive text-destructive-foreground grid place-items-center shadow"
          >
            <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <!-- Gravando -->
      <div v-if="estadoAudio === 'recording'" class="flex items-center gap-3 border border-input rounded-xl bg-background px-3.5 py-2 min-h-[40px]">
        <span class="w-2 h-2 rounded-full bg-red-500 shrink-0 animate-pulse" />
        <span class="text-sm font-bold tabular-nums text-foreground">{{ formatarCronometro(tempoGravacao) }}</span>
        <span class="text-xs text-muted-foreground flex-1">Gravando áudio...</span>
        <button @click="cancelarGravacao" class="text-xs font-semibold text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted shrink-0">Cancelar</button>
        <button @click="pararGravacao" class="text-xs font-semibold text-destructive hover:bg-destructive/10 px-2 py-1 rounded-md shrink-0">Parar</button>
      </div>

      <!-- Áudio pronto -->
      <div v-else-if="estadoAudio === 'recorded'" class="flex items-center gap-2 border border-input rounded-xl bg-background px-3 py-1.5 min-h-[40px]">
        <audio v-if="audioUrl" :src="audioUrl" controls class="h-9 flex-1 min-w-0" />
        <button @click="cancelarGravacao" class="text-xs font-semibold text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted shrink-0">Descartar</button>
        <button @click="cancelarGravacao(); iniciarGravacao()" class="text-xs font-semibold text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted shrink-0">Regravar</button>
        <button @click="enviarAudioGravado" class="text-xs font-bold text-primary hover:bg-primary/10 px-2.5 py-1.5 rounded-md shrink-0">Enviar áudio</button>
      </div>

      <!-- Enviando áudio -->
      <div v-else-if="estadoAudio === 'uploading'" class="flex items-center gap-2.5 border border-input rounded-xl bg-background px-3.5 py-2 min-h-[40px] text-sm text-muted-foreground">
        <svg class="w-4 h-4 animate-spin text-primary" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" /><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" /></svg>
        Enviando áudio...
      </div>

      <!-- Composer normal -->
      <div v-else class="flex items-end gap-1.5 sm:gap-2">
        <div
          class="flex-1 min-w-0 border border-input rounded-xl bg-background transition focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20"
          :class="isDraggingOver ? 'border-primary border-dashed bg-primary/5' : ''"
          @dragover.prevent="isDraggingOver = true"
          @dragenter.prevent="isDraggingOver = true"
          @dragleave="isDraggingOver = false"
          @drop.prevent="handleDrop"
        >
          <textarea
            ref="textareaRef"
            v-model="entrada"
            rows="1"
            :disabled="!canalConectado || enviandoTexto || enviandoLote"
            :placeholder="imagensPendentes.length ? 'Adicione uma legenda (opcional)…' : 'Digite uma mensagem…'"
            class="block w-full px-3 py-2 text-sm bg-transparent border-none outline-none resize-none overflow-y-auto min-h-[40px] max-h-[10.5rem] leading-[21px] text-foreground placeholder:text-muted-foreground disabled:opacity-50"
            @keydown="handleEnter"
            @input="autoResize"
            @paste="handlePasteTextarea"
          />
        </div>

        <input
          ref="fileInputRef"
          type="file"
          multiple
          accept="image/*,video/mp4,video/webm,video/quicktime,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.txt,.zip,.rar"
          class="hidden"
          @change="handleFileSelect"
        />

        <div ref="anexoMenuRef" class="relative shrink-0">
          <div v-if="mostrarMenuAnexo" class="absolute z-20 bottom-full right-0 mb-2 w-48 bg-popover border border-border rounded-xl shadow-xl py-1.5">
            <button @click="abrirSeletorArquivo" class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground hover:bg-muted text-left">
              <svg class="w-4 h-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></svg>
              Buscar arquivo
            </button>
            <button @click="abrirCamera" class="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground hover:bg-muted text-left">
              <svg class="w-4 h-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" /><circle cx="12" cy="13" r="4" /></svg>
              Tirar foto
            </button>
          </div>
          <button
            @click="mostrarMenuAnexo = !mostrarMenuAnexo"
            :disabled="!canalConectado"
            title="Anexar"
            class="w-10 h-10 rounded-lg grid place-items-center text-muted-foreground hover:text-foreground hover:bg-muted transition disabled:opacity-40"
          >
            <svg class="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg>
          </button>
        </div>

        <button
          v-if="!imagensPendentes.length"
          @click="iniciarGravacao"
          :disabled="!canalConectado"
          title="Gravar áudio"
          class="w-10 h-10 rounded-lg grid place-items-center text-muted-foreground hover:text-foreground hover:bg-muted transition disabled:opacity-40 shrink-0"
        >
          <svg class="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" /></svg>
        </button>

        <button
          @click="enviar"
          :disabled="!canalConectado || (!entrada.trim() && !imagensPendentes.length) || enviandoTexto || enviandoLote"
          title="Enviar"
          class="w-10 h-10 rounded-lg grid place-items-center transition shrink-0 disabled:opacity-40"
          :class="(entrada.trim() || imagensPendentes.length) ? 'bg-primary text-primary-foreground hover:bg-primary/90' : 'bg-muted text-muted-foreground'"
        >
          <svg v-if="!enviandoTexto && !enviandoLote" class="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13" /><path d="M22 2l-7 20-4-9-9-4 20-7z" /></svg>
          <svg v-else class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" /><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" /></svg>
        </button>
      </div>
      <p class="text-[10.5px] text-muted-foreground text-center mt-1.5">Enter envia · Shift+Enter quebra linha</p>
    </div>
  </div>

  <!-- Câmera -->
  <Teleport to="body">
    <div v-if="mostrarCamera" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" @click.self="fecharCamera">
      <div class="w-full max-w-md bg-card border border-border rounded-2xl overflow-hidden shadow-2xl">
        <div class="flex items-center justify-between px-4 py-3 border-b border-border">
          <span class="text-sm font-bold text-foreground">Tirar foto</span>
          <button @click="fecharCamera" class="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition" title="Fechar">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
          </button>
        </div>
        <div class="aspect-[4/3] bg-black relative">
          <video v-if="!fotoCapturada" ref="cameraVideoRef" autoplay playsinline muted class="w-full h-full object-cover" />
          <img v-else :src="fotoCapturada" class="w-full h-full object-cover" alt="Foto capturada" />
        </div>
        <div v-if="!fotoCapturada" class="flex items-center justify-center py-4">
          <button @click="tirarFoto" title="Capturar" class="w-14 h-14 rounded-full bg-white border-4 border-border hover:border-primary transition" />
        </div>
        <div v-else class="flex gap-2 p-3">
          <button @click="refazerFoto" class="flex-1 py-2 rounded-lg border border-border text-sm font-semibold text-foreground hover:bg-muted transition">Tentar de novo</button>
          <button @click="usarFoto" class="flex-1 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition">Usar foto</button>
        </div>
      </div>
    </div>
  </Teleport>
  <canvas ref="cameraCanvasRef" class="hidden" />
</template>
