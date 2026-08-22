<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useConversas, type Aba, type Conversa, type Mensagem } from '~/composables/useConversas'
import { useProfissionais } from '~/composables/useProfissionais'
import { useRealtimeConversas } from '~/composables/useRealtimeConversas'
import { useAuth } from '~/composables/useAuth'

const { conversas, isLoading, fetchConversas } = useConversas()
const { profissionais, fetchProfissionais } = useProfissionais()
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

const canaisComProfissional = computed(() =>
  profissionais.value.filter((p) => p.instancia).map((p) => ({ id: p.instancia!.id, nome: p.nome, status: p.instancia!.status }))
)

// ── Setas de rolagem das pills (com 10 profissionais elas não cabem numa linha só) ──
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

watch(canaisComProfissional, () => nextTick(atualizarSetasPills))

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
    // best-effort: zera localmente; o backend zera de fato quando o painel de
    // detalhes/abrir marca a conversa como vista (fora do escopo desta rodada).
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

// ── Tempo real ───────────────────────────────────────────────────────────────
let offMensagem: (() => void) | null = null
let offConversa: (() => void) | null = null

onMounted(async () => {
  tickAgora = setInterval(() => { agora.value = Date.now() }, 15000)
  await fetchProfissionais({ silent: true })
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
    if (payload.type === 'DELETE') {
      conversas.value = conversas.value.filter((c) => c.id !== rec.id)
      return
    }
    const idx = conversas.value.findIndex((c) => c.id === rec.id)
    if (idx >= 0) {
      // Preserva os embeds (instancia/profissional) que o broadcast não traz.
      conversas.value[idx] = { ...conversas.value[idx], ...rec }
    } else if (aba.value === 'todas' || (aba.value === 'nao_atribuidas' && !rec.assigned_to_professional_id)) {
      carregarLista({ silent: true })
    }
  })
})

onUnmounted(async () => {
  if (tickAgora) clearInterval(tickAgora)
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
        <div class="relative">
          <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/></svg>
          <input
            v-model="busca"
            @input="onBuscaInput"
            type="text"
            placeholder="Buscar por nome ou telefone..."
            class="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>

        <!-- Pills de canal/profissional -->
        <div v-if="canaisComProfissional.length" class="relative flex items-center gap-1">
          <button
            v-if="podeRolarEsquerda"
            @click="rolarPills(-1)"
            class="shrink-0 z-10 p-1 rounded-full border border-border bg-card text-muted-foreground hover:text-foreground shadow-sm"
            title="Ver profissionais anteriores"
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
              v-for="c in canaisComProfissional"
              :key="c.id"
              @click="instanciaSelecionada = c.id"
              class="shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition"
              :class="instanciaSelecionada === c.id ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:text-foreground'"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="c.status === 'connected' ? 'bg-green-400' : 'bg-muted-foreground/50'" />
              {{ c.nome }}
            </button>
          </div>

          <button
            v-if="podeRolarDireita"
            @click="rolarPills(1)"
            class="shrink-0 z-10 p-1 rounded-full border border-border bg-card text-muted-foreground hover:text-foreground shadow-sm"
            title="Ver mais profissionais"
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
        <div v-if="isLoading" class="p-4 space-y-2">
          <div v-for="i in 5" :key="i" class="h-16 bg-muted/30 rounded-xl animate-pulse" />
        </div>
        <div v-else-if="!conversas.length" class="text-center py-16 px-4">
          <p class="text-sm text-muted-foreground">Nenhuma conversa por aqui.</p>
        </div>
        <template v-else>
          <button
            v-for="c in conversas"
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
              <div v-if="canaisComProfissional.length > 1 || estaPausada(c) || c.profissional?.nome" class="flex items-center gap-1 flex-wrap mt-1">
                <!-- Badge de Canal (só quando há mais de 1 número/profissional) -->
                <span
                  v-if="canaisComProfissional.length > 1 && c.instancia"
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
    />
  </div>
</template>
