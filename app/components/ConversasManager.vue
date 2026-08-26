<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useConversas, type Aba, type Conversa, type Mensagem } from '~/composables/useConversas'
import { useProfissionais } from '~/composables/useProfissionais'
import { useCanais } from '~/composables/useCanais'
import { useRealtimeConversas } from '~/composables/useRealtimeConversas'
import { useAuth } from '~/composables/useAuth'

const { conversas, isLoading, fetchConversas, marcarLida } = useConversas()
const { profissionais, fetchProfissionais } = useProfissionais()
const { canais, fetchCanais } = useCanais()
const { subscribe, unsubscribe, onMensagem, onConversa } = useRealtimeConversas()
const { user } = useAuth()

const aba = ref<Aba>('todas')
const instanciaSelecionada = ref<string | null>(null)
const busca = ref('')
const conversaSelecionadaId = ref<string | null>(null)
const mostrarDetalhes = ref(false)
// Tipagem solta de propósito: só usamos o método exposto (adicionarMensagemRealtime).
const chatRef = ref<{ adicionarMensagemRealtime?: (m: Mensagem) => void } | null>(null)

// O dono só precisa de Todas (o que está acontecendo agora) e Arquivadas (pra
// onde a conversa vai ao clicar em "Arquivar" nos detalhes). "Não atribuídas" e
// "Resolvidas" ficam prontas no backend, só escondidas — reabilitar é só
// descomentar a linha abaixo.
const MOSTRAR_ABAS = true
const ABAS: { id: Aba; label: string }[] = [
  { id: 'todas', label: 'Todas' },
  // { id: 'nao_atribuidas', label: 'Não atribuídas' },
  // { id: 'resolvidas', label: 'Resolvidas' },
  { id: 'arquivadas', label: 'Arquivadas' }
]

// Pills de canal do filtro: TODOS os canais do usuário (por profissional e de
// disparo), menos os de uso exclusivo de notificação — esses nunca acumulam
// conversa (o webhook ignora mensagens neles, ver `uso_notificacao` no back).
// Prioriza o nome do PROFISSIONAL quando o canal está vinculado a um (mais
// reconhecível na lista do que o nome interno da instância).
const nomeProfissionalPorInstancia = computed(() => {
  const mapa = new Map<string, string>()
  for (const p of profissionais.value) {
    if (p.instancia) mapa.set(p.instancia.id, p.nome)
  }
  return mapa
})

// Ordem alfabética pelo nome exibido (profissional ou nome da instância) —
// com vários canais de disparo junto dos de profissional, a ordem de criação
// virava bagunça visual; ordenado fica fácil de achar o canal certo.
const canaisFiltro = computed(() =>
  canais.value
    .filter((c) => !c.uso_notificacao)
    .map((c) => ({
      id: c.id,
      nome: nomeProfissionalPorInstancia.value.get(c.id) || c.nome,
      telefone: c.telefone,
      status: c.status
    }))
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR', { sensitivity: 'base' }))
)

// ── Setas de rolagem das pills (com vários canais elas não cabem numa linha só) ──
const pillsScrollRef = ref<HTMLElement | null>(null)
const podeRolarEsquerda = ref(false)
const podeRolarDireita = ref(false)

function atualizarSetasPills() {
  const el = pillsScrollRef.value
  if (!el) return
  podeRolarEsquerda.value = el.scrollLeft > 4
  podeRolarDireita.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 4
}

function rolarPills(direcao: 1 | -1) {
  pillsScrollRef.value?.scrollBy({ left: direcao * 160, behavior: 'smooth' })
}

watch(canaisFiltro, () => nextTick(atualizarSetasPills))

// ── Relógio local para os badges de pausa dos cards (sem depender de refresh) ──
const agora = ref(Date.now())
let tickAgora: ReturnType<typeof setInterval> | null = null

function estaPausada(c: Conversa): boolean {
  if (!c.tempo_pausa || !c.tempo_pausa_inicio) return false
  return new Date(c.tempo_pausa_inicio).getTime() + c.tempo_pausa * 1000 > agora.value
}

function pausaPermanente(c: Conversa): boolean {
  return (c.tempo_pausa || 0) >= 60 * 60 * 24 * 300
}

let debounceBusca: ReturnType<typeof setTimeout> | null = null
function onBuscaInput() {
  if (debounceBusca) clearTimeout(debounceBusca)
  debounceBusca = setTimeout(() => carregarLista(), 350)
}

// ── Filtro de período (por data da última mensagem) ─────────────────────────
// Filtra sobre a lista já carregada (client-side) — mesmo raciocínio do
// filtro de busca: a lista de conversas do canal por profissional não é
// grande o bastante pra justificar ida ao banco a cada troca de período.
type FiltroPeriodo = 'todos' | 'hoje' | '7d' | '30d' | 'custom'
const PERIODOS: { id: FiltroPeriodo; label: string }[] = [
  { id: 'todos', label: 'Todos' },
  { id: 'hoje', label: 'Hoje' },
  { id: '7d', label: '7 dias' },
  { id: '30d', label: '30 dias' },
  { id: 'custom', label: 'Personalizado' }
]
const filtroPeriodo = ref<FiltroPeriodo>('todos')
const filtroDataInicio = ref('')
const filtroDataFim = ref('')
const mostrarFiltroPeriodo = ref(false)
const filtroPeriodoRef = ref<HTMLElement | null>(null)

const filtroPeriodoAtivo = computed(() => filtroPeriodo.value !== 'todos')

const intervaloFiltroPeriodo = computed<{ inicioMs: number; fimMs: number } | null>(() => {
  const modo = filtroPeriodo.value
  if (modo === 'todos') return null
  if (modo === 'custom') {
    if (!filtroDataInicio.value && !filtroDataFim.value) return null
    const inicioMs = filtroDataInicio.value ? new Date(`${filtroDataInicio.value}T00:00:00`).getTime() : 0
    const fimMs = filtroDataFim.value ? new Date(`${filtroDataFim.value}T23:59:59`).getTime() : Number.MAX_SAFE_INTEGER
    return { inicioMs, fimMs }
  }
  if (modo === 'hoje') {
    const hoje = new Date()
    hoje.setHours(0, 0, 0, 0)
    return { inicioMs: hoje.getTime(), fimMs: Date.now() }
  }
  const dias = modo === '7d' ? 7 : 30
  const fimMs = Date.now()
  return { inicioMs: fimMs - dias * 86400000, fimMs }
})

// Conversa sem data conhecida (ultimo_horario/created_at) nunca é escondida —
// mesma regra do filtro de período do Agzap: melhor mostrar de mais do que
// sumir com uma conversa por falta de metadado.
const conversasExibidas = computed(() => {
  const intervalo = intervaloFiltroPeriodo.value
  if (!intervalo) return conversas.value
  return conversas.value.filter((c) => {
    const ref = c.ultimo_horario || c.created_at
    if (!ref) return true
    const ms = new Date(ref).getTime()
    if (Number.isNaN(ms)) return true
    return ms >= intervalo.inicioMs && ms <= intervalo.fimMs
  })
})

function escolherPeriodo(p: FiltroPeriodo) {
  filtroPeriodo.value = p
  if (p !== 'custom') mostrarFiltroPeriodo.value = false
}

function limparFiltroPeriodo() {
  filtroPeriodo.value = 'todos'
  filtroDataInicio.value = ''
  filtroDataFim.value = ''
  mostrarFiltroPeriodo.value = false
}

function onClickForaFiltroPeriodo(e: MouseEvent) {
  if (mostrarFiltroPeriodo.value && filtroPeriodoRef.value && !filtroPeriodoRef.value.contains(e.target as Node)) {
    mostrarFiltroPeriodo.value = false
  }
}

async function carregarLista(opts?: { silent?: boolean }) {
  await fetchConversas({
    aba: aba.value,
    instanciaId: instanciaSelecionada.value,
    busca: busca.value.trim() || undefined,
    silent: opts?.silent
  })
}

watch([aba, instanciaSelecionada], () => carregarLista())

const conversaSelecionada = computed(() => conversas.value.find((c) => c.id === conversaSelecionadaId.value) || null)

function selecionar(c: Conversa) {
  conversaSelecionadaId.value = c.id
  if (c.nao_lidas > 0) {
    c.nao_lidas = 0
    // Persiste no banco — sem isso, ao trocar de aba/página e voltar, a lista
    // recarrega do banco com o contador antigo e o badge "volta" sozinho.
    marcarLida(c.id).catch(() => {})
  }
}

function fecharChat() {
  conversaSelecionadaId.value = null
  mostrarDetalhes.value = false
}

function onConversaAtualizada(atualizado: Conversa) {
  const idx = conversas.value.findIndex((c) => c.id === atualizado.id)
  if (idx >= 0) conversas.value[idx] = { ...conversas.value[idx], ...atualizado }
}

function onConversaExcluida(id: string) {
  conversas.value = conversas.value.filter((c) => c.id !== id)
  if (conversaSelecionadaId.value === id) fecharChat()
}

// ── Tempo real ───────────────────────────────────────────────────────────────
let offMensagem: (() => void) | null = null
let offConversa: (() => void) | null = null

onMounted(async () => {
  tickAgora = setInterval(() => { agora.value = Date.now() }, 15000)
  document.addEventListener('click', onClickForaFiltroPeriodo)
  await Promise.all([fetchProfissionais({ silent: true }), fetchCanais({ silent: true })])
  await nextTick(atualizarSetasPills)
  await carregarLista()

  if (user.value?.id) {
    await subscribe(user.value.id)
  }

  offMensagem = onMensagem((payload) => {
    if (payload.type !== 'INSERT') return
    const msg = payload.record as Mensagem
    chatRef.value?.adicionarMensagemRealtime?.(msg)
  })

  offConversa = onConversa((payload) => {
    const rec = payload.record as Conversa
    if (!rec?.id) return
    if (payload.type === 'DELETE' || rec.deleted_at) {
      conversas.value = conversas.value.filter((c) => c.id !== rec.id)
      if (conversaSelecionadaId.value === rec.id) fecharChat()
      return
    }
    const idx = conversas.value.findIndex((c) => c.id === rec.id)
    if (idx >= 0) {
      // Preserva os embeds (instancia/profissional) que o broadcast não traz.
      conversas.value[idx] = { ...conversas.value[idx], ...rec }
      // Conversa aberta na tela: o dono já está vendo, não conta como "não
      // lida" mesmo que o trigger tenha acabado de incrementar (mensagem nova
      // chegou enquanto o painel estava aberto). Persiste o zero de novo pra
      // não voltar ao recarregar a lista depois.
      if (rec.id === conversaSelecionadaId.value && conversas.value[idx].nao_lidas > 0) {
        conversas.value[idx].nao_lidas = 0
        marcarLida(rec.id).catch(() => {})
      }
    } else if (aba.value === 'todas' || (aba.value === 'nao_atribuidas' && !rec.assigned_to_professional_id)) {
      carregarLista({ silent: true })
    }
  })
})

onUnmounted(async () => {
  if (tickAgora) clearInterval(tickAgora)
  document.removeEventListener('click', onClickForaFiltroPeriodo)
  offMensagem?.()
  offConversa?.()
  await unsubscribe()
})

function formatarHorario(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const hoje = new Date()
  const mesmodia = d.toDateString() === hoje.toDateString()
  if (mesmodia) return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

function previewMensagem(c: Conversa): string {
  return c.ultima_mensagem || 'Sem mensagens ainda'
}
</script>

<template>
  <div class="h-[calc(100vh-8rem)] min-h-[520px] flex rounded-2xl border border-border overflow-hidden bg-card">
    <!-- Coluna 1: lista -->
    <div
      class="w-full lg:w-[360px] shrink-0 border-r border-border flex flex-col"
      :class="conversaSelecionadaId ? 'hidden lg:flex' : 'flex'"
    >
      <div class="p-4 border-b border-border space-y-3 shrink-0">
        <div class="flex items-center gap-2">
          <div class="relative flex-1">
            <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/></svg>
            <input
              v-model="busca"
              @input="onBuscaInput"
              type="text"
              placeholder="Buscar por nome ou telefone..."
              class="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>

          <!-- Filtro de período -->
          <div ref="filtroPeriodoRef" class="relative shrink-0">
            <button
              @click="mostrarFiltroPeriodo = !mostrarFiltroPeriodo"
              class="relative p-2 rounded-lg border transition"
              :class="filtroPeriodoAtivo ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:text-foreground hover:bg-muted'"
              title="Filtrar por período"
            >
              <Icon icon="filter" class-name="w-4 h-4" fallback="⏳" />
              <span v-if="filtroPeriodoAtivo" class="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-primary" />
            </button>

            <div
              v-if="mostrarFiltroPeriodo"
              class="absolute right-0 z-20 mt-2 w-64 bg-card border border-border rounded-xl shadow-lg p-3 space-y-3"
            >
              <div>
                <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Período</p>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="p in PERIODOS"
                    :key="p.id"
                    @click="escolherPeriodo(p.id)"
                    class="px-2.5 py-1 rounded-full text-xs font-medium border transition"
                    :class="filtroPeriodo === p.id ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:text-foreground'"
                  >{{ p.label }}</button>
                </div>
              </div>

              <div v-if="filtroPeriodo === 'custom'" class="flex items-center gap-1.5">
                <input
                  v-model="filtroDataInicio"
                  type="date"
                  class="flex-1 min-w-0 px-2 py-1.5 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <span class="text-xs text-muted-foreground shrink-0">até</span>
                <input
                  v-model="filtroDataFim"
                  type="date"
                  class="flex-1 min-w-0 px-2 py-1.5 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              <button
                v-if="filtroPeriodoAtivo"
                @click="limparFiltroPeriodo"
                class="w-full text-center px-2.5 py-1.5 rounded-lg text-xs font-medium border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition"
              >Limpar filtro</button>
            </div>
          </div>
        </div>

        <!-- Pills de canal (por profissional e de disparo) -->
        <div v-if="canaisFiltro.length" class="relative flex items-center gap-1">
          <button
            v-if="podeRolarEsquerda"
            @click="rolarPills(-1)"
            class="shrink-0 z-10 p-1 rounded-full border border-border bg-card text-muted-foreground hover:text-foreground shadow-sm"
            title="Ver canais anteriores"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7"/></svg>
          </button>

          <div ref="pillsScrollRef" @scroll="atualizarSetasPills" class="flex gap-1.5 overflow-x-auto pb-1 scroll-smooth">
            <button
              @click="instanciaSelecionada = null"
              class="shrink-0 px-2.5 py-1 rounded-full text-xs font-medium border transition"
              :class="!instanciaSelecionada ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:text-foreground'"
            >Todos</button>
            <button
              v-for="c in canaisFiltro"
              :key="c.id"
              @click="instanciaSelecionada = c.id"
              class="shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition"
              :class="instanciaSelecionada === c.id ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:text-foreground'"
              :title="c.telefone ? `${c.nome} — ${c.telefone}` : c.nome"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="c.status === 'conectado' ? 'bg-green-400' : 'bg-muted-foreground/50'" />
              {{ c.nome }}
            </button>
          </div>

          <button
            v-if="podeRolarDireita"
            @click="rolarPills(1)"
            class="shrink-0 z-10 p-1 rounded-full border border-border bg-card text-muted-foreground hover:text-foreground shadow-sm"
            title="Ver mais canais"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7"/></svg>
          </button>
        </div>

        <!-- Abas (só aparece se houver mais de 1 — ver MOSTRAR_ABAS) -->
        <div v-if="MOSTRAR_ABAS" class="flex gap-1 overflow-x-auto">
          <button
            v-for="a in ABAS"
            :key="a.id"
            @click="aba = a.id"
            class="shrink-0 px-2.5 py-1.5 rounded-lg text-xs font-medium transition"
            :class="aba === a.id ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted'"
          >{{ a.label }}</button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="isLoading" class="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
          <svg class="w-7 h-7 animate-spin text-primary" fill="none" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
            <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
          </svg>
          <p class="text-sm font-medium">Carregando...</p>
        </div>
        <div v-else-if="!conversasExibidas.length" class="text-center py-16 px-4">
          <p class="text-sm text-muted-foreground">{{ filtroPeriodoAtivo ? 'Nenhuma conversa nesse período.' : 'Nenhuma conversa por aqui.' }}</p>
        </div>
        <template v-else>
          <button
            v-for="c in conversasExibidas"
            :key="c.id"
            @click="selecionar(c)"
            class="w-full flex items-center gap-3 p-3 border-b border-border/60 text-left hover:bg-muted/40 transition"
            :class="conversaSelecionadaId === c.id ? 'bg-primary/5' : ''"
          >
            <div class="relative shrink-0">
              <AvatarContato :nome="c.nome_contato" :numero="c.numero" :photo="c.photo" size-class="w-11 h-11 text-sm" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2">
                <p class="font-medium text-foreground text-sm truncate">{{ c.nome_contato || c.numero }}</p>
                <span class="text-[11px] text-muted-foreground shrink-0">{{ formatarHorario(c.ultimo_horario) }}</span>
              </div>
              <div class="flex items-center justify-between gap-2 mt-0.5">
                <p class="text-xs text-muted-foreground truncate">{{ previewMensagem(c) }}</p>
                <span v-if="c.nao_lidas > 0" class="shrink-0 min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-bold flex items-center justify-center">
                  {{ c.nao_lidas }}
                </span>
              </div>
              <div v-if="canaisFiltro.length > 1 || estaPausada(c) || c.profissional?.nome" class="flex items-center gap-1 flex-wrap mt-1">
                <!-- Badge de Canal (só quando há mais de 1 canal) -->
                <span
                  v-if="canaisFiltro.length > 1 && c.instancia"
                  class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-medium leading-none border border-border text-muted-foreground"
                  :title="c.instancia.status === 'connected' ? `${c.instancia.nome_instancia} — Online` : `${c.instancia.nome_instancia} — Offline`"
                >
                  <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="c.instancia.status === 'connected' ? 'bg-emerald-500' : 'bg-red-500'" />
                  {{ c.instancia.nome_instancia }}
                </span>

                <!-- Badge de pausa (humano no controle / IA pausada) -->
                <span
                  v-if="estaPausada(c)"
                  class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold leading-none bg-amber-500/10 text-amber-700 dark:text-amber-400"
                >
                  ⏸ {{ pausaPermanente(c) ? 'Pausada permanente' : 'Pausada' }}
                </span>

                <!-- Badge de atribuição -->
                <span
                  v-if="c.profissional?.nome"
                  class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold leading-none bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 truncate max-w-[140px]"
                >
                  {{ c.profissional.nome }}
                </span>
              </div>
            </div>
          </button>
        </template>
      </div>
    </div>

    <!-- Coluna 2: chat -->
    <div class="flex-1 min-w-0" :class="conversaSelecionadaId ? 'flex flex-col' : 'hidden lg:flex lg:flex-col'">
      <template v-if="conversaSelecionada">
        <div class="lg:hidden p-2 border-b border-border">
          <button @click="fecharChat" class="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground px-2 py-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
            Voltar
          </button>
        </div>
        <ChatConversa
          ref="chatRef"
          :conversa="conversaSelecionada"
          @abrir-detalhes="mostrarDetalhes = true"
        />
      </template>
      <div v-else class="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        Selecione uma conversa para ver o histórico
      </div>
    </div>

    <!-- Painel de detalhes (flutuante) -->
    <DetalhesConversa
      v-if="mostrarDetalhes && conversaSelecionada"
      :conversa="conversaSelecionada"
      @close="mostrarDetalhes = false"
      @atualizado="onConversaAtualizada"
      @excluida="onConversaExcluida"
    />
  </div>
</template>
