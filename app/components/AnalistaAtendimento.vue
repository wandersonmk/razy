<script setup lang="ts">
/**
 * Analista de Atendimento — bolha fixa no canto que abre um painel lateral.
 *
 * Painel lateral (e não popup pequeno) porque a resposta é densa: diagnóstico
 * de conversa tem ~10 campos e comparação de vendedores vem em tabela. Num
 * balão de 380px isso vira rolagem infinita.
 *
 * Fica montado no layout do dashboard, então acompanha o dono em qualquer
 * página — a pergunta costuma nascer olhando outra tela ("e esse cliente aqui?").
 */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAnalista, exportarAnalisePDF, exportarSessaoPDF, type TurnoAnalista } from '~/composables/useAnalista'
import { useConversaAtiva, formatarTelefoneBR } from '~/composables/useConversaAtiva'

const { turnos, resumo, pensando, carregarResumo, perguntar, limpar } = useAnalista()
const { conversaAtiva } = useConversaAtiva()

const aberto = ref(false)
const ampliado = ref(false)
const entrada = ref('')
const corpoRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const exportando = ref<string | null>(null)

let toast: any = null
onMounted(async () => {
  toast = await useToastSafe()
})

// Catálogo de partida. Chat vazio trava as pessoas — e o dono não tem como
// adivinhar que dá pra perguntar "quem recebeu orçamento e sumiu".
//
// O primeiro grupo é CONTEXTUAL: com uma conversa aberta na tela, ele fala do
// cliente daquela conversa (é de lá que a dúvida nasce). Sem conversa aberta,
// não inventa telefone — oferece o caminho de buscar por nome/número.
const CATALOGO = computed<{ titulo: string; icone: string; perguntas: string[] }[]>(() => {
  const c = conversaAtiva.value
  // Telefone formatado nas perguntas: o backend normaliza (so_digitos +
  // variantes do nono dígito), então o que importa aqui é ficar legível.
  const tel = c ? formatarTelefoneBR(c.numero) : ''
  const cliente = c
    ? {
        titulo: `Sobre ${c.nome || tel}`,
        icone: 'user',
        perguntas: [
          `Como está o atendimento do telefone ${tel}?`,
          `Na conversa do telefone ${tel}, o que ficou sem resposta?`,
          `O cliente do telefone ${tel} tem chance de fechar?`,
          `Resuma a conversa do telefone ${tel}`
        ]
      }
    : {
        titulo: 'Sobre um cliente',
        icone: 'user',
        perguntas: [
          'Abra uma conversa para eu analisar aquele cliente',
          'Quais clientes estão sem retorno há mais tempo?'
        ]
      }

  return [
    cliente,
    {
      titulo: 'Sobre um vendedor',
      icone: 'chart',
      perguntas: [
        'Analise o desempenho de cada vendedor',
        'Quais vendedores estão sem movimento hoje?'
      ]
    },
    {
      // SDR = canal do WhatsApp sem profissional vinculado (criado direto na
      // aba Canais, não na página Profissionais). Grupo separado do vendedor
      // porque são conjuntos de canais diferentes — um não entra na conta do outro.
      titulo: 'Sobre os SDRs',
      icone: 'sdr',
      perguntas: [
        'Analise o desempenho de cada SDR',
        'Quantos atendimentos os SDRs têm aberto no total?',
        'Quais SDRs estão sem movimento hoje?'
      ]
    },
    {
      titulo: 'Sobre o funil',
      icone: 'funnel',
      perguntas: [
        'Quais conversas estão paradas há mais de 3 dias?',
        'Onde estou perdendo cliente?'
      ]
    }
  ]
})

// A sugestão "abra uma conversa" não é pergunta: só orienta e devolve o foco
// pro campo, pra pessoa digitar o número que quiser.
const DICA_ABRIR_CONVERSA = 'Abra uma conversa para eu analisar aquele cliente'

/**
 * Cor de cada grupo do catálogo — a mesma do card que aquela pergunta produz
 * (cliente → azul da visão geral, vendedor → verde do desempenho, funil →
 * âmbar do que precisa de atenção). Assim o caminho da pergunta até a resposta
 * é o mesmo tom, em vez de o painel abrir todo azul e responder colorido.
 *
 * Fica no repouso quase neutro: só o título e o ícone carregam cor; a caixa
 * do botão acende no hover.
 */
const GRUPO_CLASSES: Record<string, { titulo: string; icone: string; botao: string }> = {
  user: {
    titulo: 'text-blue-600 dark:text-blue-400',
    icone: 'text-blue-500',
    botao: 'border-blue-500/20 bg-blue-500/[0.04] hover:border-blue-500/50 hover:bg-blue-500/[0.09]'
  },
  chart: {
    titulo: 'text-emerald-600 dark:text-emerald-400',
    icone: 'text-emerald-500',
    botao: 'border-emerald-500/20 bg-emerald-500/[0.04] hover:border-emerald-500/50 hover:bg-emerald-500/[0.09]'
  },
  sdr: {
    titulo: 'text-indigo-600 dark:text-indigo-400',
    icone: 'text-indigo-500',
    botao: 'border-indigo-500/20 bg-indigo-500/[0.04] hover:border-indigo-500/50 hover:bg-indigo-500/[0.09]'
  },
  funnel: {
    titulo: 'text-amber-600 dark:text-amber-400',
    icone: 'text-amber-500',
    botao: 'border-amber-500/25 bg-amber-500/[0.05] hover:border-amber-500/50 hover:bg-amber-500/[0.10]'
  }
}

const GRUPO_NEUTRO = {
  titulo: 'text-foreground',
  icone: 'text-muted-foreground',
  botao: 'border-border bg-background hover:border-primary hover:bg-primary/5'
}

// Grupo novo sem cor definida cai no neutro em vez de derrubar o painel.
const grupoClasses = (icone: string) => GRUPO_CLASSES[icone] || GRUPO_NEUTRO

const temConversa = computed(() => turnos.value.length > 0)

const coberturaResumo = computed(() => {
  const r = resumo.value
  if (!r || !r.total_msgs || !r.msgs_sem_texto) return null
  return { pct: r.cobertura_pct ?? 0, sem: r.msgs_sem_texto, total: r.total_msgs }
})

function formatarMin(min: number | null | undefined): string {
  if (min == null) return '—'
  if (min < 60) return `${Math.round(min)} min`
  const h = Math.floor(min / 60)
  return `${h}h ${Math.round(min % 60)}min`
}

/**
 * Os quatro números da abertura.
 *
 * A cor sai do VALOR, não do rótulo: um mesmo indicador fica verde ou vermelho
 * conforme o estado da operação. Tint só onde há julgamento — "conversas
 * ativas" é escala, não bom nem ruim, então fica neutro. Sem isso a cor vira
 * enfeite e para de significar coisa alguma.
 */
type TomTile = 'neutro' | 'bom' | 'atencao' | 'ruim'

const TILE_CLASSES: Record<TomTile, { caixa: string; numero: string }> = {
  neutro:  { caixa: 'border-border bg-background',            numero: 'text-foreground' },
  bom:     { caixa: 'border-emerald-500/25 bg-emerald-500/[0.07]', numero: 'text-emerald-600 dark:text-emerald-400' },
  atencao: { caixa: 'border-amber-500/30 bg-amber-500/[0.08]',     numero: 'text-amber-600 dark:text-amber-400' },
  ruim:    { caixa: 'border-rose-500/25 bg-rose-500/[0.07]',       numero: 'text-rose-600 dark:text-rose-400' }
}

const tiles = computed(() => {
  const r = resumo.value
  if (!r) return []

  const paradas = r.paradas_3d ?? null
  const resp = r.resposta_media_min ?? null

  const tomParadas: TomTile =
    paradas == null ? 'neutro' : paradas === 0 ? 'bom' : paradas > 5 ? 'ruim' : 'atencao'

  // Faixas de tempo de resposta: até 1h é bom, até 2h pede atenção, acima
  // disso o cliente já desistiu de esperar.
  const tomResposta: TomTile =
    resp == null ? 'neutro' : resp <= 60 ? 'bom' : resp <= 120 ? 'atencao' : 'ruim'

  return [
    { valor: r.ativas ?? '—', rotulo: 'conversas ativas', tom: 'neutro' as TomTile },
    { valor: r.movimento_24h ?? '—', rotulo: 'com movimento hoje', tom: (r.movimento_24h ? 'bom' : 'neutro') as TomTile },
    { valor: paradas ?? '—', rotulo: 'paradas +3 dias', tom: tomParadas },
    { valor: formatarMin(resp), rotulo: 'resposta média', tom: tomResposta }
  ]
})

async function rolarFim() {
  await nextTick()
  const el = corpoRef.value
  if (el) el.scrollTop = el.scrollHeight
}

/**
 * Traz o COMEÇO de um turno para o topo da área de leitura.
 *
 * Rolar para o fim é o certo num chat de mensagens curtas, mas aqui a resposta
 * vem em vários cards: o dono caía no último deles e podia achar que era tudo,
 * sem perceber que havia conteúdo acima. Ancorando a pergunta no topo, ele lê
 * de cima para baixo e rola no sentido natural.
 */
async function rolarParaTopoDo(id: string) {
  await nextTick()
  const cont = corpoRef.value
  const alvo = cont?.querySelector<HTMLElement>(`[data-turno="${id}"]`)
  if (!cont || !alvo) return rolarFim()
  // getBoundingClientRect em vez de offsetTop: não depende de qual ancestral
  // está posicionado, então não quebra se o layout do painel mudar.
  const deslocamento = alvo.getBoundingClientRect().top - cont.getBoundingClientRect().top
  cont.scrollTop += deslocamento - 8
}

watch(
  () => turnos.value.length,
  async (agora, antes) => {
    if (agora <= (antes ?? 0)) return
    const ultimo = turnos.value[agora - 1]
    if (!ultimo) return

    // Pergunta recém-enviada: desce, para a pessoa ver o que escreveu e o
    // "consultando...". Resposta que chegou: sobe até a pergunta que a gerou.
    if (ultimo.papel === 'user') return rolarFim()

    const pergunta = turnos.value[agora - 2]
    await rolarParaTopoDo(pergunta?.papel === 'user' ? pergunta.id : ultimo.id)
  }
)

watch(pensando, (ativo) => { if (ativo) rolarFim() })

function abrir() {
  aberto.value = true
  if (!resumo.value) carregarResumo()
  nextTick(() => inputRef.value?.focus())
}

function fechar() {
  aberto.value = false
}

async function enviar(texto?: string) {
  const p = (texto ?? entrada.value).trim()
  if (!p || pensando.value) return

  // Dica, não pergunta: prepara o campo em vez de mandar pro LLM.
  if (p === DICA_ABRIR_CONVERSA) {
    entrada.value = 'Como está o atendimento do telefone '
    inputRef.value?.focus()
    return
  }

  entrada.value = ''
  await perguntar(p)
}

function novaConversa() {
  limpar()
  carregarResumo()
  nextTick(() => inputRef.value?.focus())
}

async function baixarPDF(turno: TurnoAnalista, indice: number) {
  // A pergunta que gerou a resposta é o turno imediatamente anterior.
  const pergunta = turnos.value[indice - 1]?.texto || turno.titulo || 'Análise de atendimento'
  exportando.value = turno.id
  try {
    await exportarAnalisePDF(turno, pergunta)
    toast?.success?.('Relatório baixado')
  } catch (e) {
    console.error('[analista] falha ao gerar PDF:', e)
    toast?.error?.('Não consegui gerar o PDF. Tente de novo.')
  } finally {
    exportando.value = null
  }
}

// Respostas que valem relatório. Turno com erro não é análise — se ele contasse,
// o botão de sessão apareceria numa tela onde nada deu certo.
const respostasValidas = computed(
  () => turnos.value.filter((t) => t.papel === 'assistant' && !t.erro).length
)

async function baixarSessaoPDF() {
  exportando.value = 'sessao'
  try {
    await exportarSessaoPDF(turnos.value)
    toast?.success?.('Análise completa baixada')
  } catch (e) {
    console.error('[analista] falha ao gerar PDF da sessão:', e)
    toast?.error?.('Não consegui gerar o PDF. Tente de novo.')
  } finally {
    exportando.value = null
  }
}

/**
 * Markdown → HTML para exibir a resposta.
 *
 * Escapa o HTML ANTES de aplicar o markdown: o texto é gerado por um LLM que
 * acabou de ler mensagens escritas por terceiros. Nada que venha de lá pode
 * virar tag no painel do dono.
 */
function renderizar(md: string): string {
  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  const linhas = esc(md || '').split('\n')
  const out: string[] = []
  let lista = false
  let tabela = false

  const fecharLista = () => { if (lista) { out.push('</ul>'); lista = false } }
  const fecharTabela = () => { if (tabela) { out.push('</tbody></table></div>'); tabela = false } }

  const inline = (s: string) =>
    s
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[\s(])\*([^*]+?)\*(?=[\s.,;:)]|$)/g, '$1<em>$2</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>')

  for (let i = 0; i < linhas.length; i++) {
    const t = (linhas[i] || '').trim()

    if (!t) { fecharLista(); fecharTabela(); continue }

    const proxima = (linhas[i + 1] || '').trim()
    if (t.startsWith('|') && /^\|[\s:|-]+\|$/.test(proxima)) {
      fecharLista(); fecharTabela()
      const celulas = (l: string) => l.replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
      out.push('<div class="tabela-scroll"><table><thead><tr>')
      for (const c of celulas(t)) out.push(`<th>${inline(c)}</th>`)
      out.push('</tr></thead><tbody>')
      tabela = true
      i++
      continue
    }

    if (tabela && t.startsWith('|')) {
      const celulas = t.replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
      out.push('<tr>' + celulas.map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>')
      continue
    }
    fecharTabela()

    if (/^#{1,6}\s/.test(t)) {
      fecharLista()
      out.push(`<h4>${inline(t.replace(/^#+\s*/, ''))}</h4>`)
      continue
    }

    if (/^[-*+]\s+/.test(t) || /^\d+\.\s+/.test(t)) {
      if (!lista) { out.push('<ul>'); lista = true }
      out.push(`<li>${inline(t.replace(/^([-*+]|\d+\.)\s+/, ''))}</li>`)
      continue
    }

    fecharLista()
    out.push(`<p>${inline(t)}</p>`)
  }
  fecharLista()
  fecharTabela()
  return out.join('')
}

function onTeclaGlobal(e: KeyboardEvent) {
  if (e.key === 'Escape' && aberto.value) fechar()
}

onMounted(() => document.addEventListener('keydown', onTeclaGlobal))
onUnmounted(() => document.removeEventListener('keydown', onTeclaGlobal))
</script>

<template>
  <div>
    <!-- Bolha -->
    <button
      v-show="!aberto"
      @click="abrir"
      class="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/40 flex items-center justify-center hover:-translate-y-0.5 hover:scale-105 transition-transform focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background"
      title="Analista de Atendimento"
      aria-label="Abrir o Analista de Atendimento"
    >
      <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /><path d="M8.5 11.5l2 2 4-4.5" />
      </svg>
    </button>

    <!-- Véu -->
    <transition enter-active-class="transition-opacity duration-200" leave-active-class="transition-opacity duration-200" enter-from-class="opacity-0" leave-to-class="opacity-0">
      <div v-if="aberto" @click="fechar" class="fixed inset-0 z-40 bg-black/40" />
    </transition>

    <!-- Painel -->
    <transition enter-active-class="transition-transform duration-300 ease-out" leave-active-class="transition-transform duration-200 ease-in" enter-from-class="translate-x-full" leave-to-class="translate-x-full">
      <aside
        v-if="aberto"
        class="fixed top-0 right-0 bottom-0 z-50 bg-card border-l border-border flex flex-col shadow-2xl w-full"
        :class="ampliado ? 'sm:w-[min(980px,100vw)]' : 'sm:w-[min(700px,100vw)]'"
        role="dialog"
        aria-label="Analista de Atendimento"
      >
        <!-- Cabeçalho -->
        <header class="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0">
          <div class="w-8 h-8 rounded-lg bg-primary text-primary-foreground grid place-items-center shrink-0">
            <svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /><path d="M8.5 11.5l2 2 4-4.5" />
            </svg>
          </div>
          <div class="min-w-0">
            <p class="text-sm font-bold text-foreground leading-tight">Analista de Atendimento</p>
            <p class="text-[11px] text-muted-foreground flex items-center gap-1.5">
              <span v-if="resumo?.ativas != null" class="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              {{ resumo?.ativas != null ? `Lendo ${resumo.ativas} conversas` : 'Pergunte sobre os atendimentos' }}
            </p>
          </div>

          <div class="ml-auto flex items-center gap-0.5">
            <button
              @click="ampliado = !ampliado"
              class="hidden sm:grid w-8 h-8 rounded-lg place-items-center text-muted-foreground hover:text-foreground hover:bg-muted transition"
              :title="ampliado ? 'Reduzir' : 'Ampliar'"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path v-if="!ampliado" d="M15 3h6v6M21 3l-7 7M9 21H3v-6M3 21l7-7" />
                <path v-else d="M14 10h6M20 10l-7-7M10 14H4M4 14l7 7" />
              </svg>
            </button>
            <button
              v-if="temConversa"
              @click="novaConversa"
              class="w-8 h-8 rounded-lg grid place-items-center text-muted-foreground hover:text-foreground hover:bg-muted transition"
              title="Nova conversa"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 12a9 9 0 1 0 2.6-6.4" /><path d="M3 3v5h5" />
              </svg>
            </button>
            <button
              @click="fechar"
              class="w-8 h-8 rounded-lg grid place-items-center text-muted-foreground hover:text-foreground hover:bg-muted transition"
              title="Fechar"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </header>

        <!-- Corpo -->
        <div ref="corpoRef" class="flex-1 overflow-y-auto px-4 py-4 space-y-4">

          <!-- Abertura: resumo + catálogo -->
          <template v-if="!temConversa">
            <div>
              <p class="text-[15px] font-semibold text-foreground">O que você quer saber?</p>
              <p class="text-[13px] text-muted-foreground mt-1">Clique numa pergunta ou escreva a sua.</p>
            </div>

            <!-- Contexto: a conversa que está aberta atrás do painel -->
            <div v-if="conversaAtiva" class="flex items-center gap-2.5 rounded-xl border border-primary/30 bg-primary/5 px-3 py-2.5">
              <div class="w-8 h-8 rounded-full bg-primary/15 text-primary grid place-items-center text-[11px] font-bold shrink-0">
                {{ (conversaAtiva.nome || '?').slice(0, 2).toUpperCase() }}
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-[13px] font-semibold text-foreground truncate">
                  {{ conversaAtiva.nome || formatarTelefoneBR(conversaAtiva.numero) }}
                </p>
                <p class="text-[11.5px] text-muted-foreground truncate">
                  {{ formatarTelefoneBR(conversaAtiva.numero) }}<template v-if="conversaAtiva.vendedor"> · {{ conversaAtiva.vendedor }}</template>
                </p>
              </div>
              <span class="text-[10px] font-bold uppercase tracking-wide text-primary bg-primary/10 px-2 py-1 rounded shrink-0">Aberta</span>
            </div>

            <div v-if="tiles.length" class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div
                v-for="(t, i) in tiles"
                :key="i"
                class="rounded-xl border px-3 py-2.5"
                :class="TILE_CLASSES[t.tom].caixa"
              >
                <p class="text-xl font-bold tabular-nums leading-tight" :class="TILE_CLASSES[t.tom].numero">{{ t.valor }}</p>
                <p class="text-[11px] text-muted-foreground leading-tight">{{ t.rotulo }}</p>
              </div>
            </div>

            <div v-if="coberturaResumo" class="flex gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2.5">
              <svg class="w-4 h-4 text-amber-500 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
              </svg>
              <div class="min-w-0">
                <p class="text-[12.5px] font-bold text-amber-600 dark:text-amber-400 leading-snug">
                  Consigo ler {{ coberturaResumo.pct }}% do histórico
                </p>
                <p class="text-[12px] text-muted-foreground mt-0.5">
                  {{ coberturaResumo.sem }} mensagens são áudio sem transcrição ou imagem sem legenda.
                </p>
              </div>
            </div>

            <div class="space-y-3.5">
              <div v-for="g in CATALOGO" :key="g.titulo" class="space-y-1.5">
                <p class="text-xs font-bold flex items-center gap-2" :class="grupoClasses(g.icone).titulo">
                  <svg class="w-3.5 h-3.5 shrink-0" :class="grupoClasses(g.icone).icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <template v-if="g.icone === 'user'"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></template>
                    <template v-else-if="g.icone === 'chart'"><path d="M3 3v18h18" /><path d="M7 14l4-4 3 3 5-6" /></template>
                    <template v-else-if="g.icone === 'sdr'"><path d="M3 18v-6a9 9 0 0 1 18 0v6" /><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" /></template>
                    <template v-else><path d="M3 4h18l-7 8v7l-4 2v-9z" /></template>
                  </svg>
                  {{ g.titulo }}
                </p>
                <div class="grid sm:grid-cols-2 gap-1.5">
                  <button
                    v-for="p in g.perguntas"
                    :key="p"
                    @click="enviar(p)"
                    class="text-left text-[12.5px] leading-snug px-3 py-2.5 rounded-lg border transition"
                    :class="grupoClasses(g.icone).botao"
                  >{{ p }}</button>
                </div>
              </div>
            </div>
          </template>

          <!-- Conversa -->
          <template v-for="(t, i) in turnos" :key="t.id">
            <div v-if="t.papel === 'user'" :data-turno="t.id" class="flex justify-end">
              <p class="max-w-[85%] bg-primary text-primary-foreground text-[13.5px] px-3.5 py-2 rounded-2xl rounded-br-sm">{{ t.texto }}</p>
            </div>

            <div v-else :data-turno="t.id" class="space-y-3">
              <!-- O rastro das consultas NÃO aparece aqui: polui a leitura de quem
                   só quer a resposta. Ele continua sendo gravado no turno e vai
                   inteiro no PDF, onde serve de auditoria para quem receber o
                   relatório e quiser saber de onde cada número saiu. -->

              <!-- Cobertura -->
              <div v-if="t.cobertura && t.cobertura.sem_conteudo > 0" class="flex gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2.5">
                <svg class="w-4 h-4 text-amber-500 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
                </svg>
                <div class="min-w-0 flex-1">
                  <p class="text-[12.5px] font-bold text-amber-600 dark:text-amber-400 leading-snug">
                    Li {{ t.cobertura.lidas }} de {{ t.cobertura.total }} mensagens
                  </p>
                  <p class="text-[12px] text-muted-foreground mt-0.5">
                    {{ t.cobertura.sem_conteudo }} sem conteúdo legível (áudio sem transcrição ou imagem sem legenda).
                  </p>
                  <div class="h-1 rounded-full bg-muted overflow-hidden mt-2">
                    <div class="h-full bg-amber-500 rounded-full" :style="{ width: Math.round((t.cobertura.lidas / t.cobertura.total) * 100) + '%' }" />
                  </div>
                </div>
              </div>

              <!-- Resposta em cards temáticos. O markdown corrido continua
                   como reserva: é o que aparece em caso de erro e enquanto o
                   ai-service estiver numa versão anterior aos cards. -->
              <div v-if="!t.erro && t.cards?.length" class="space-y-2.5">
                <CardAnalista v-for="(c, n) in t.cards" :key="n" :card="c" />
              </div>
              <div
                v-else
                class="analista-md text-[13.5px] leading-relaxed"
                :class="t.erro ? 'text-destructive' : 'text-foreground'"
                v-html="renderizar(t.texto)"
              />

              <!-- Gráficos: vêm depois do texto porque confirmam a conclusão,
                   não substituem a leitura. Em duas colunas quando o painel
                   está ampliado e há mais de um. -->
              <div
                v-if="t.graficos?.length"
                class="grid gap-2.5"
                :class="ampliado && t.graficos.length > 1 ? 'sm:grid-cols-2' : 'grid-cols-1'"
              >
                <GraficoAnalista v-for="(g, n) in t.graficos" :key="n" :spec="g" />
              </div>

              <!-- Exportar -->
              <div v-if="!t.erro" class="flex justify-end">
                <button
                  @click="baixarPDF(t, i)"
                  :disabled="exportando === t.id"
                  class="inline-flex items-center gap-2 text-[12px] font-semibold text-primary bg-primary/10 hover:bg-primary/15 border border-transparent hover:border-primary/40 rounded-lg px-3 py-1.5 transition disabled:opacity-60"
                >
                  <svg v-if="exportando !== t.id" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M7 10l5 5 5-5" /><path d="M12 15V3" />
                  </svg>
                  <svg v-else class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
                    <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
                  </svg>
                  {{ exportando === t.id ? 'Gerando...' : (respostasValidas > 1 ? 'Baixar esta resposta' : 'Baixar PDF') }}
                </button>
              </div>
            </div>
          </template>

          <!-- Exportar a sessão inteira.
               Só a partir da 2ª resposta: com uma só, este PDF seria idêntico
               ao do botão acima e a escolha viraria dúvida sem motivo. -->
          <div v-if="respostasValidas > 1 && !pensando" class="pt-1">
            <button
              @click="baixarSessaoPDF"
              :disabled="exportando === 'sessao'"
              class="w-full inline-flex items-center justify-center gap-2 text-[12px] font-semibold text-foreground bg-muted/60 hover:bg-muted border border-border hover:border-primary/40 rounded-lg px-3 py-2 transition disabled:opacity-60"
            >
              <svg v-if="exportando !== 'sessao'" class="w-3.5 h-3.5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><path d="M9 15h6M9 11h3" />
              </svg>
              <svg v-else class="w-3.5 h-3.5 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
              </svg>
              {{ exportando === 'sessao' ? 'Gerando análise completa...' : `Baixar análise completa (${respostasValidas} respostas)` }}
            </button>
          </div>

          <!-- Pensando -->
          <div v-if="pensando" class="flex items-center gap-2.5 text-[12.5px] text-muted-foreground">
            <svg class="w-3.5 h-3.5 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
              <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
            </svg>
            Consultando os atendimentos...
          </div>
        </div>

        <!-- Rodapé -->
        <footer class="border-t border-border px-3 py-3 shrink-0 space-y-2">
          <div class="flex items-center gap-2 bg-background border border-border rounded-xl px-3 py-2 focus-within:border-primary transition">
            <input
              ref="inputRef"
              v-model="entrada"
              @keydown.enter="enviar()"
              :disabled="pensando"
              type="text"
              placeholder="Pergunte sobre um cliente, vendedor ou período..."
              class="flex-1 min-w-0 bg-transparent border-0 outline-none text-foreground text-[13.5px] placeholder:text-muted-foreground disabled:opacity-60"
            />
            <button
              @click="enviar()"
              :disabled="pensando || !entrada.trim()"
              class="w-8 h-8 rounded-lg bg-primary text-primary-foreground grid place-items-center shrink-0 disabled:opacity-40 transition"
              aria-label="Enviar"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 12h15M13 6l6 6-6 6" />
              </svg>
            </button>
          </div>
          <p class="text-[10.5px] text-muted-foreground text-center">
            Responde com base nas mensagens gravadas. Sempre mostra o que leu.
          </p>
        </footer>
      </aside>
    </transition>
  </div>
</template>

<style scoped>
/* Estilos da resposta em markdown. `deep` porque o HTML entra via v-html. */
.analista-md :deep(p) { margin: 0 0 0.6rem; }
.analista-md :deep(p:last-child) { margin-bottom: 0; }
.analista-md :deep(h4) { font-size: 13.5px; font-weight: 700; margin: 1rem 0 0.4rem; }
.analista-md :deep(h4:first-child) { margin-top: 0; }
.analista-md :deep(ul) { margin: 0 0 0.6rem; padding-left: 1.1rem; list-style: disc; }
.analista-md :deep(li) { margin-bottom: 0.25rem; }
.analista-md :deep(strong) { font-weight: 600; }
.analista-md :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.88em;
  background: rgb(var(--color-muted));
  padding: 0.1em 0.35em;
  border-radius: 4px;
}
.analista-md :deep(.tabela-scroll) {
  overflow-x: auto;
  border: 1px solid rgb(var(--color-border));
  border-radius: 10px;
  margin: 0 0 0.7rem;
}
.analista-md :deep(table) { border-collapse: collapse; width: 100%; font-size: 12.5px; }
.analista-md :deep(th) {
  text-align: left;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgb(var(--color-muted-fg));
  background: rgb(var(--color-muted));
  padding: 0.55rem 0.7rem;
  white-space: nowrap;
}
.analista-md :deep(td) {
  padding: 0.55rem 0.7rem;
  border-top: 1px solid rgb(var(--color-border));
  font-variant-numeric: tabular-nums;
}
</style>
