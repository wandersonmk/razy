<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useCampanhas } from '~/composables/useCampanhas'
import { usePublicos } from '~/composables/usePublicos'
import { useCanais } from '~/composables/useCanais'
import type { Campanha } from '~/composables/useCampanhas'

const { campanhas, isLoading, fetchCampanhas, criarCampanha, atualizarStatus, excluirCampanha } = useCampanhas()
const { publicos, fetchPublicos } = usePublicos()
const { canais, fetchCanais } = useCanais()

let toast: any

// ── Atualização em tempo real (polling silencioso enquanto há disparo ativo) ──
const recemDisparado = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  toast = await useToastSafe()
  await Promise.all([fetchCampanhas(), fetchPublicos(), fetchCanais()])

  // A cada 3s, recarrega (sem piscar) se houver campanha em andamento ou recém-disparada.
  pollTimer = setInterval(() => {
    const ativa = campanhas.value.some((c) => c.status === 'em_andamento')
    if (ativa || recemDisparado.value) fetchCampanhas({ silent: true })
  }, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const canaisConectados = computed(() => canais.value.filter((c) => c.status === 'conectado'))

// Resumo dos canais para o modal de confirmação. Espelha o ai-service:
//  • rodízio  = conectados que NÃO são de uso exclusivo de notificação (são esses que disparam)
//  • desconectados = não entram no envio
//  • notificacao   = reservados para avisar o atendente (não disparam a campanha)
const resumoCanais = computed(() => {
  const todos = canais.value
  const rodizio = todos.filter((c) => c.status === 'conectado' && !c.uso_notificacao)
  const desconectados = todos.filter((c) => c.status !== 'conectado')
  const notificacao = todos.filter((c) => c.uso_notificacao)
  return { rodizio, desconectados, notificacao }
})

// ── Modal Criar Campanha ─────────────────────────────────────────────────────
const showModalCriar = ref(false)
const criando = ref(false)
const form = ref({
  nome: '',
  publico_id: '',
  canal_id: '',
  modo_mensagem: 'manual' as 'manual' | 'ia',
  mensagem: '',
  intervalo_segundos: 10,
  agendar: false,
  agendado_para: '',
  usar_roteamento: false,
  alternar_canais: false
})

function abrirModalCriar() {
  form.value = { nome: '', publico_id: '', canal_id: '', modo_mensagem: 'manual', mensagem: '', intervalo_segundos: 10, agendar: false, agendado_para: '', usar_roteamento: false, alternar_canais: false }
  showModalCriar.value = true
}

// ── Estratégia de canais (roteamento × alternância) ─────────────────────────
// Ambas exigem ≥ 2 canais CONECTADOS. Se não houver, abre modal orientando.
const modalCanaisInsuficientes = ref<{ show: boolean; recurso: string }>({ show: false, recurso: '' })

function ativarRoteamento() {
  if (form.value.usar_roteamento) { form.value.usar_roteamento = false; return }
  if (canaisConectados.value.length < 2) {
    modalCanaisInsuficientes.value = { show: true, recurso: 'o roteamento automático' }
    return
  }
  form.value.usar_roteamento = true
  form.value.alternar_canais = false // mutuamente exclusivos
}

function ativarAlternancia() {
  if (form.value.alternar_canais) { form.value.alternar_canais = false; return }
  if (canaisConectados.value.length < 2) {
    modalCanaisInsuficientes.value = { show: true, recurso: 'a alternância de números' }
    return
  }
  form.value.alternar_canais = true
  form.value.usar_roteamento = false // mutuamente exclusivos
}

// Canal único só é exigido quando nenhuma estratégia multi-canal está ativa.
const usaMultiCanal = computed(() => form.value.usar_roteamento || form.value.alternar_canais)

const publicoSelecionado = computed(() =>
  publicos.value.find((p) => p.id === form.value.publico_id)
)

const formValido = computed(() => {
  if (!form.value.nome || !form.value.publico_id) return false
  // Canal obrigatório apenas quando nenhuma estratégia multi-canal está ativa
  if (!usaMultiCanal.value && !form.value.canal_id) return false
  if (form.value.modo_mensagem === 'manual' && !form.value.mensagem) return false
  if (form.value.agendar && !form.value.agendado_para) return false
  return true
})

async function confirmarCriar() {
  if (!formValido.value) {
    toast?.warning(
      form.value.modo_mensagem === 'manual'
        ? 'Preencha nome, público, canal e mensagem'
        : 'Preencha nome, público e canal'
    )
    return
  }
  criando.value = true
  try {
    await criarCampanha({
      nome: form.value.nome,
      publico_id: form.value.publico_id,
      canal_id: usaMultiCanal.value ? undefined : form.value.canal_id,
      modo_mensagem: form.value.modo_mensagem,
      mensagem: form.value.modo_mensagem === 'manual' ? form.value.mensagem : null,
      intervalo_segundos: form.value.intervalo_segundos,
      agendado_para: form.value.agendar && form.value.agendado_para
        ? new Date(form.value.agendado_para).toISOString()
        : null,
      usar_roteamento: form.value.usar_roteamento,
      alternar_canais: form.value.alternar_canais
    })
    toast?.success('Campanha criada!')
    showModalCriar.value = false
    await fetchCampanhas()
  } catch {
    toast?.error('Erro ao criar campanha')
  } finally {
    criando.value = false
  }
}

// ── Disparo (orquestrado pelo ai-service) ─────────────────────────────────────
const campanhaEmDisparo = ref<string | null>(null)
const showModalDisparo = ref(false)
const campanhaDisparo = ref<Campanha | null>(null)

// A campanha em confirmação usa rodízio/roteamento? (mostra o resumo de canais no modal)
const disparoMultiCanal = computed(
  () => !!(campanhaDisparo.value?.alternar_canais || campanhaDisparo.value?.usar_roteamento)
)

const verificandoCanais = ref(false)

async function iniciarDisparo(campanha: Campanha) {
  // Revalida o status dos canais ao vivo (/api/instancias consulta a UAzAPI) para que
  // tanto a checagem abaixo quanto o resumo do modal reflitam a realidade do momento.
  verificandoCanais.value = true
  try {
    await fetchCanais({ silent: true })
  } finally {
    verificandoCanais.value = false
  }

  // Alternância (round-robin) e roteamento (failover) não usam canal_id fixo:
  // o ai-service escolhe entre os canais conectados na hora do disparo.
  if (campanha.alternar_canais || campanha.usar_roteamento) {
    // Espelha o ai-service (get_canais_conectados): só canais conectados que NÃO são
    // de uso exclusivo de notificação contam como disponíveis para disparo.
    const disponiveis = canaisConectados.value.filter((c) => !c.uso_notificacao)
    if (disponiveis.length === 0) {
      toast?.error('Nenhum canal conectado disponível para o disparo. Conecte um canal em Configurações.')
      return
    }
  } else {
    if (!campanha.canal_id) {
      toast?.error('Esta campanha não tem canal vinculado')
      return
    }
    const canal = canais.value.find((c) => c.id === campanha.canal_id)
    if (!canal || canal.status !== 'conectado') {
      toast?.error('O canal vinculado não está conectado. Verifique em Configurações.')
      return
    }
  }
  campanhaDisparo.value = campanha
  showModalDisparo.value = true
}

async function confirmarDisparo() {
  const campanha = campanhaDisparo.value!
  showModalDisparo.value = false
  campanhaEmDisparo.value = campanha.id
  try {
    const supabase = useSupabaseClient()
    const { data: sess } = await supabase.auth.getSession()
    const headers: Record<string, string> = sess.session?.access_token
      ? { Authorization: `Bearer ${sess.session.access_token}` }
      : {}

    // Chama o server route, que repassa pro ai-service com o INTERNAL_TOKEN.
    await $fetch(`/api/campanhas/${campanha.id}/iniciar`, { method: 'POST', headers })

    toast?.success('Disparo iniciado! As mensagens serão enviadas em segundo plano pelo servidor.')
    // Liga o polling por ~15s até o status virar "em andamento" (o loop continua sozinho depois).
    recemDisparado.value = true
    setTimeout(() => { recemDisparado.value = false }, 15000)
    await fetchCampanhas({ silent: true })
  } catch (e: any) {
    toast?.error(e?.data?.statusMessage || e?.data?.message || 'Erro ao iniciar disparo')
  } finally {
    campanhaEmDisparo.value = null
  }
}

async function pausarCampanha(id: string) {
  await atualizarStatus(id, 'pausada')
  toast?.info('Campanha pausada')
}

const confirmModal = ref({
  show: false,
  title: '',
  message: '',
  loading: false,
  onConfirm: async () => {}
})

async function executarConfirm() {
  confirmModal.value.loading = true
  try {
    await confirmModal.value.onConfirm()
    confirmModal.value.show = false
  } catch {
    /* erro já tratado */
  } finally {
    confirmModal.value.loading = false
  }
}

function solicitarExcluir(campanha: Campanha) {
  confirmModal.value = {
    show: true,
    loading: false,
    title: 'Excluir Campanha',
    message: `Remover a campanha "${campanha.nome}" da lista? As métricas dela (enviados, falhas e respostas) continuam preservadas nos Relatórios e no Dashboard.`,
    onConfirm: async () => {
      try {
        await excluirCampanha(campanha.id)
        toast?.success('Campanha removida da lista (métricas preservadas)')
      } catch {
        toast?.error('Erro ao excluir')
        throw new Error()
      }
    }
  }
}

// ── Modal Detalhes + Logs ─────────────────────────────────────────────────────
const showModalDetalhes = ref(false)
const campanhaDetalhes = ref<Campanha | null>(null)
const abaDetalhes = ref<'info' | 'logs'>('info')
const logs = ref<any[]>([])
const carregandoLogs = ref(false)

async function verDetalhes(c: Campanha) {
  campanhaDetalhes.value = c
  abaDetalhes.value = 'info'
  logs.value = []
  showModalDetalhes.value = true
}

async function carregarLogs() {
  if (!campanhaDetalhes.value || carregandoLogs.value) return
  carregandoLogs.value = true
  try {
    const supabase = useSupabaseClient()
    const { data: sess } = await supabase.auth.getSession()
    const headers: Record<string, string> = sess.session?.access_token
      ? { Authorization: `Bearer ${sess.session.access_token}` }
      : {}
    const data = await $fetch<{ logs: any[] }>(`/api/campanhas/${campanhaDetalhes.value.id}/logs`, { headers })
    logs.value = data.logs || []
  } catch {
    logs.value = []
  } finally {
    carregandoLogs.value = false
  }
}

function trocarAba(aba: 'info' | 'logs') {
  abaDetalhes.value = aba
  if (aba === 'logs' && logs.value.length === 0) carregarLogs()
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const statusConfig: Record<string, { label: string; color: string }> = {
  rascunho:     { label: 'Rascunho',     color: 'bg-muted text-muted-foreground' },
  em_andamento: { label: 'Em andamento', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
  concluida:    { label: 'Concluída',    color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
  pausada:      { label: 'Pausada',      color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' },
  falhou:       { label: 'Falhou',       color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' }
}

function taxaEnvio(c: Campanha) {
  const total = c.total_enviados + c.total_falhas
  return total > 0 ? Math.round((c.total_enviados / total) * 100) : 0
}

function inserirVariavel(v: string) {
  form.value.mensagem += `{${v}}`
}
</script>

<template>
  <div class="space-y-6">
    <!-- Ação (o título "Campanhas" já vem do header da página) -->
    <div class="flex items-center justify-end">
      <button
        @click="abrirModalCriar"
        class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition text-sm font-medium"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Nova Campanha
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-28 bg-card rounded-xl border border-border animate-pulse"/>
    </div>

    <!-- Empty -->
    <div v-else-if="campanhas.length === 0" class="text-center py-16">
      <svg class="w-12 h-12 mx-auto text-muted-foreground/40 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
      </svg>
      <p class="text-muted-foreground">Nenhuma campanha criada ainda</p>
    </div>

    <!-- Lista Campanhas -->
    <div v-else class="space-y-3">
      <div
        v-for="c in campanhas"
        :key="c.id"
        class="bg-card border border-border rounded-xl p-5 hover:border-primary/30 transition"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h3 class="font-semibold text-foreground truncate">{{ c.nome }}</h3>
              <span :class="['inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full font-medium shrink-0', statusConfig[c.status]?.color]">
                <svg
                  v-if="c.status === 'em_andamento'"
                  class="w-3 h-3 animate-spin"
                  fill="none" viewBox="0 0 24 24"
                >
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ statusConfig[c.status]?.label }}
              </span>
            </div>
            <p class="text-sm text-muted-foreground">
              Público: <span class="text-foreground">{{ (c as any).publico?.nome || '—' }}</span>
            </p>
            <p v-if="c.agendado_para && c.status === 'rascunho'" class="text-xs text-primary mt-1 flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              Agendada: {{ new Date(c.agendado_para).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) }}
            </p>
          </div>

          <!-- Métricas -->
          <div class="hidden sm:flex items-center gap-6 text-center shrink-0">
            <div>
              <p class="text-lg font-bold text-green-500">{{ c.total_enviados }}</p>
              <p class="text-xs text-muted-foreground">Enviados</p>
            </div>
            <div>
              <p class="text-lg font-bold text-red-500">{{ c.total_falhas }}</p>
              <p class="text-xs text-muted-foreground">Falhas</p>
            </div>
            <div v-if="c.total_respostas > 0">
              <p class="text-lg font-bold text-primary">{{ c.total_respostas }}</p>
              <p class="text-xs text-muted-foreground">Respostas</p>
            </div>
            <div v-if="c.total_enviados + c.total_falhas > 0">
              <p class="text-lg font-bold text-amber-500">{{ taxaEnvio(c) }}%</p>
              <p class="text-xs text-muted-foreground">Taxa</p>
            </div>
          </div>
        </div>

        <!-- Indicador de início (o disparo roda em segundo plano no servidor) -->
        <div v-if="campanhaEmDisparo === c.id" class="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <span>Iniciando disparo no servidor...</span>
        </div>

        <!-- Ações -->
        <div class="flex items-center gap-2 mt-3 pt-3 border-t border-border">
          <button
            v-if="c.status === 'rascunho' || c.status === 'pausada'"
            @click="iniciarDisparo(c)"
            :disabled="campanhaEmDisparo !== null || verificandoCanais"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50"
          >
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            {{ verificandoCanais ? 'Verificando canais...' : 'Disparar' }}
          </button>
          <button
            v-if="c.status === 'falhou'"
            @click="iniciarDisparo(c)"
            :disabled="campanhaEmDisparo !== null || verificandoCanais"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition disabled:opacity-50"
            title="Continua de onde parou — contatos já enviados não serão repetidos"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            Tentar novamente
          </button>
          <button
            v-if="c.status === 'em_andamento'"
            @click="pausarCampanha(c.id)"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition"
          >
            Pausar
          </button>
          <button
            @click="verDetalhes(c)"
            class="px-3 py-1.5 text-xs font-medium border border-border rounded-lg text-foreground hover:bg-muted transition"
          >
            Detalhes
          </button>
          <button
            v-if="c.status !== 'em_andamento'"
            @click="solicitarExcluir(c)"
            class="ml-auto p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- ── Modal Criar Campanha ── -->
    <Teleport to="body">
      <div v-if="showModalCriar" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div class="bg-card border border-border rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
          <div class="flex items-center justify-between p-6 border-b border-border">
            <h3 class="text-lg font-semibold">Nova Campanha</h3>
            <button @click="showModalCriar = false" class="text-muted-foreground hover:text-foreground transition">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="p-6 space-y-4">
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Nome da Campanha <span class="text-red-500">*</span></label>
              <AppInput v-model="form.nome" placeholder="Ex: Reativação Clientes Maio..." />
            </div>

            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Público <span class="text-red-500">*</span></label>
              <select
                v-model="form.publico_id"
                class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="">Selecione um público...</option>
                <option v-for="p in publicos" :key="p.id" :value="p.id">
                  {{ p.nome }} ({{ p.total_contatos }} contatos)
                </option>
              </select>
            </div>

            <!-- Estratégia de envio entre canais -->
            <div class="rounded-xl border border-border p-4 space-y-3">
              <p class="text-sm font-medium text-foreground">Estratégia de envio</p>

              <!-- Roteamento automático (failover) -->
              <div class="flex items-center justify-between gap-3">
                <div class="flex-1">
                  <p class="text-sm text-foreground">Roteamento automático de canais</p>
                  <p class="text-xs text-muted-foreground mt-0.5">Se um número for bloqueado ou desconectado, troca para o próximo canal conectado e continua o disparo.</p>
                </div>
                <button
                  type="button"
                  @click="ativarRoteamento"
                  :class="[
                    'relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none',
                    form.usar_roteamento ? 'bg-primary' : 'bg-muted'
                  ]"
                >
                  <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.usar_roteamento ? 'translate-x-5' : 'translate-x-0']"/>
                </button>
              </div>

              <div class="border-t border-border"/>

              <!-- Alternância de números (round-robin) -->
              <div class="flex items-center justify-between gap-3">
                <div class="flex-1">
                  <p class="text-sm text-foreground">Alternância de números durante o disparo</p>
                  <p class="text-xs text-muted-foreground mt-0.5">Distribui os envios entre todos os canais conectados (1º contato → canal 1, 2º → canal 2…), reduzindo o risco de bloqueio em listas grandes.</p>
                </div>
                <button
                  type="button"
                  @click="ativarAlternancia"
                  :class="[
                    'relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none',
                    form.alternar_canais ? 'bg-primary' : 'bg-muted'
                  ]"
                >
                  <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.alternar_canais ? 'translate-x-5' : 'translate-x-0']"/>
                </button>
              </div>

              <!-- Info da estratégia ativa -->
              <div v-if="usaMultiCanal" class="flex items-start gap-2 text-xs p-2 rounded-lg bg-primary/5 border border-primary/20 text-foreground">
                <svg class="w-3.5 h-3.5 shrink-0 mt-0.5 text-primary" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
                <span>
                  Usando <strong>{{ canaisConectados.length }} canal(is) conectado(s)</strong>.
                  {{ form.alternar_canais ? 'Os envios serão alternados entre eles.' : 'Um canal por vez, com troca automática em caso de bloqueio.' }}
                  Se um número cair durante o disparo, o servidor pula para o próximo automaticamente.
                </span>
              </div>
            </div>

            <!-- Canal de envio (apenas quando não há estratégia multi-canal) -->
            <div v-if="!usaMultiCanal">
              <label class="block text-sm font-medium text-foreground mb-1">Canal de Envio <span class="text-red-500">*</span></label>
              <select
                v-model="form.canal_id"
                class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                :disabled="canaisConectados.length === 0"
              >
                <option value="">{{ canaisConectados.length === 0 ? 'Nenhum canal conectado' : 'Selecione um canal...' }}</option>
                <option v-for="c in canaisConectados" :key="c.id" :value="c.id">
                  {{ c.nome }} {{ c.telefone ? `— ${c.telefone}` : '' }}
                </option>
              </select>
              <p v-if="canaisConectados.length === 0" class="text-xs text-amber-600 dark:text-amber-400 mt-1">
                <NuxtLink to="/configuracoes" class="underline">Conecte um canal em Configurações</NuxtLink> antes de criar a campanha.
              </p>
            </div>

            <!-- Modo da mensagem: manual ou gerada pela IA -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-1.5">Mensagem <span class="text-red-500">*</span></label>
              <div class="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  @click="form.modo_mensagem = 'manual'"
                  :class="[
                    'flex flex-col items-start gap-0.5 rounded-lg border p-3 text-left transition',
                    form.modo_mensagem === 'manual' ? 'border-primary bg-primary/5 ring-1 ring-primary/40' : 'border-border hover:border-primary/30'
                  ]"
                >
                  <span class="text-sm font-medium text-foreground">Mensagem manual</span>
                  <span class="text-xs text-muted-foreground">Você escreve o texto enviado</span>
                </button>
                <button
                  type="button"
                  @click="form.modo_mensagem = 'ia'"
                  :class="[
                    'flex flex-col items-start gap-0.5 rounded-lg border p-3 text-left transition',
                    form.modo_mensagem === 'ia' ? 'border-primary bg-primary/5 ring-1 ring-primary/40' : 'border-border hover:border-primary/30'
                  ]"
                >
                  <span class="text-sm font-medium text-foreground">IA decide ✨</span>
                  <span class="text-xs text-muted-foreground">Gera com base na observação</span>
                </button>
              </div>
            </div>

            <!-- Modo manual: textarea com variáveis -->
            <div v-if="form.modo_mensagem === 'manual'">
              <div class="flex flex-wrap gap-1.5 mb-2">
                <span class="text-xs text-muted-foreground">Variáveis:</span>
                <button
                  v-for="v in ['nome', 'telefone', 'empresa', 'observacao', 'etapa']"
                  :key="v"
                  type="button"
                  @click="inserirVariavel(v)"
                  class="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded hover:bg-primary/20 transition font-mono"
                >
                  {{'{'}}{{ v }}{{'}'}}
                </button>
              </div>
              <textarea
                v-model="form.mensagem"
                rows="5"
                placeholder="Olá {nome}, tudo bem? Entramos em contato porque..."
                class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
              />
              <p class="text-xs text-muted-foreground mt-1">{{ form.mensagem.length }} caracteres</p>
            </div>

            <!-- Modo IA: explicação -->
            <div
              v-else
              class="border border-primary/30 bg-primary/5 rounded-xl p-3 flex items-start gap-2 text-xs text-foreground"
            >
              <svg class="w-4 h-4 shrink-0 mt-0.5 text-primary" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z"/>
              </svg>
              <span>
                A IA vai gerar uma mensagem <strong>personalizada para cada contato</strong>, com base no campo
                <strong>observação</strong> dele. O disparo é orquestrado pelo servidor de IA, que mantém o contexto da conversa.
              </span>
            </div>

            <!-- Intervalo entre disparos -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Intervalo entre disparos</label>
              <div class="flex items-center gap-2">
                <input
                  v-model.number="form.intervalo_segundos"
                  type="number"
                  min="1"
                  class="w-24 px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <span class="text-sm text-muted-foreground">segundos entre cada mensagem</span>
              </div>
              <p class="text-xs text-muted-foreground mt-1">Intervalos maiores reduzem o risco de bloqueio do número.</p>
            </div>

            <!-- Agendamento -->
            <div class="rounded-xl border border-border p-4 space-y-3">
              <div class="flex items-center justify-between gap-3">
                <div class="flex items-center gap-2.5">
                  <div class="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <svg class="w-4.5 h-4.5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:1.125rem;height:1.125rem">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  </div>
                  <div>
                    <p class="text-sm font-medium text-foreground">Agendar início do disparo</p>
                    <p class="text-xs text-muted-foreground mt-0.5">Inicia automaticamente no horário escolhido</p>
                  </div>
                </div>
                <button
                  type="button"
                  @click="form.agendar = !form.agendar"
                  :class="[
                    'relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none',
                    form.agendar ? 'bg-primary' : 'bg-muted'
                  ]"
                >
                  <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.agendar ? 'translate-x-5' : 'translate-x-0']"/>
                </button>
              </div>
              <div v-if="form.agendar" class="pt-1">
                <input
                  v-model="form.agendado_para"
                  type="datetime-local"
                  class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <p class="text-xs text-muted-foreground mt-1.5">Se não agendar, você dispara manualmente pelo botão da campanha.</p>
              </div>
            </div>
          </div>

          <div class="flex gap-3 p-6 border-t border-border">
            <button @click="showModalCriar = false" class="flex-1 px-4 py-2 border border-border rounded-lg text-sm text-foreground hover:bg-muted transition">
              Cancelar
            </button>
            <AppButton @click="confirmarCriar" :disabled="criando || !formValido" class="flex-1">
              {{ criando ? 'Criando...' : 'Criar Campanha' }}
            </AppButton>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Modal Confirmar Disparo ── -->
    <Teleport to="body">
      <div v-if="showModalDisparo" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div class="bg-card border border-border rounded-2xl w-full max-w-sm shadow-2xl p-6 space-y-4">
          <h3 class="text-lg font-semibold text-foreground">Confirmar Disparo</h3>
          <p class="text-sm text-muted-foreground">
            Você está prestes a disparar a campanha <strong class="text-foreground">{{ campanhaDisparo?.nome }}</strong>.
            As mensagens serão enviadas com intervalo de {{ campanhaDisparo?.intervalo_segundos ?? 10 }} segundos entre cada envio.
          </p>
          <!-- Resumo dos canais (apenas rodízio / roteamento) -->
          <div v-if="disparoMultiCanal" class="rounded-lg border border-border bg-muted/40 p-3 space-y-2.5 text-xs">
            <p class="font-medium text-foreground flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>
              {{ campanhaDisparo?.alternar_canais ? 'Alternância (round-robin)' : 'Roteamento (failover)' }}
            </p>
            <div class="space-y-1">
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">🟢 Conectados no rodízio</span>
                <span class="font-semibold text-foreground tabular-nums">{{ resumoCanais.rodizio.length }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">🔴 Desconectados (fora do envio)</span>
                <span class="font-semibold text-foreground tabular-nums">{{ resumoCanais.desconectados.length }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">🔔 Notificação de atendente</span>
                <span class="font-semibold text-foreground tabular-nums">{{ resumoCanais.notificacao.length }}</span>
              </div>
            </div>
            <div v-if="resumoCanais.rodizio.length > 0" class="pt-2 border-t border-border">
              <p class="text-muted-foreground mb-1.5">Os envios serão alternados entre:</p>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="c in resumoCanais.rodizio"
                  :key="c.id"
                  class="inline-flex items-center px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 font-medium"
                >{{ c.nome }}</span>
              </div>
            </div>
            <p v-if="resumoCanais.rodizio.length === 0" class="text-red-600 dark:text-red-400 font-medium">
              ⚠️ Nenhum canal conectado disponível — o disparo vai falhar. Conecte um canal em Configurações.
            </p>
            <p v-else-if="resumoCanais.rodizio.length === 1" class="text-amber-600 dark:text-amber-400">
              ⚠️ Só há 1 canal conectado — não haverá alternância real (tudo sairá por ele).
            </p>
          </div>

          <!-- Aviso simples (canal único) -->
          <div v-else class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-xs text-amber-700 dark:text-amber-400">
            ⚠️ Certifique-se de que a instância WhatsApp está conectada antes de iniciar.
          </div>
          <div class="flex gap-3">
            <button @click="showModalDisparo = false" class="flex-1 px-4 py-2 border border-border rounded-lg text-sm text-foreground hover:bg-muted transition">
              Cancelar
            </button>
            <button @click="confirmarDisparo" class="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition">
              Iniciar Disparo
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Modal Detalhes ── -->
    <Teleport to="body">
      <div v-if="showModalDetalhes && campanhaDetalhes" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div class="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl flex flex-col max-h-[90vh]">
          <!-- Header -->
          <div class="flex items-center justify-between p-6 border-b border-border shrink-0">
            <div>
              <h3 class="text-lg font-semibold">{{ campanhaDetalhes.nome }}</h3>
              <span v-if="campanhaDetalhes.usar_roteamento || campanhaDetalhes.alternar_canais" class="inline-flex items-center gap-1 text-xs text-primary mt-0.5">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>
                {{ campanhaDetalhes.alternar_canais ? 'Alternância de canais' : 'Roteamento ativo' }}
              </span>
            </div>
            <button @click="showModalDetalhes = false" class="text-muted-foreground hover:text-foreground">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Abas -->
          <div class="flex border-b border-border shrink-0">
            <button
              @click="trocarAba('info')"
              :class="['flex-1 py-2.5 text-sm font-medium transition', abaDetalhes === 'info' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground']"
            >Informações</button>
            <button
              @click="trocarAba('logs')"
              :class="['flex-1 py-2.5 text-sm font-medium transition', abaDetalhes === 'logs' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground']"
            >Logs de Disparo</button>
          </div>

          <!-- Aba: Info -->
          <div v-if="abaDetalhes === 'info'" class="p-6 space-y-4 overflow-y-auto">
            <div class="grid grid-cols-3 gap-3 text-center">
              <div class="p-3 bg-green-50 dark:bg-green-900/20 rounded-xl">
                <p class="text-2xl font-bold text-green-600">{{ campanhaDetalhes.total_enviados }}</p>
                <p class="text-xs text-muted-foreground mt-1">Enviados</p>
              </div>
              <div class="p-3 bg-red-50 dark:bg-red-900/20 rounded-xl">
                <p class="text-2xl font-bold text-red-600">{{ campanhaDetalhes.total_falhas }}</p>
                <p class="text-xs text-muted-foreground mt-1">Falhas</p>
              </div>
              <div class="p-3 bg-primary/10 rounded-xl">
                <p class="text-2xl font-bold text-primary">{{ taxaEnvio(campanhaDetalhes) }}%</p>
                <p class="text-xs text-muted-foreground mt-1">Taxa</p>
              </div>
            </div>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-muted-foreground">Status</span>
                <span :class="statusConfig[campanhaDetalhes.status]?.color" class="px-2 py-0.5 rounded-full text-xs">
                  {{ statusConfig[campanhaDetalhes.status]?.label }}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">Estratégia de canais</span>
                <span :class="(campanhaDetalhes.usar_roteamento || campanhaDetalhes.alternar_canais) ? 'text-primary' : 'text-muted-foreground'" class="text-xs font-medium">
                  {{ campanhaDetalhes.alternar_canais ? 'Alternância (round-robin)' : campanhaDetalhes.usar_roteamento ? 'Roteamento (failover)' : 'Canal único' }}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">Criada em</span>
                <span class="text-foreground">{{ new Date(campanhaDetalhes.created_at).toLocaleDateString('pt-BR') }}</span>
              </div>
              <div v-if="campanhaDetalhes.iniciado_em" class="flex justify-between">
                <span class="text-muted-foreground">Iniciada em</span>
                <span class="text-foreground">{{ new Date(campanhaDetalhes.iniciado_em).toLocaleString('pt-BR') }}</span>
              </div>
            </div>
            <div v-if="campanhaDetalhes.mensagem" class="p-3 bg-muted/30 rounded-lg">
              <p class="text-xs text-muted-foreground mb-1">Mensagem</p>
              <p class="text-sm text-foreground whitespace-pre-wrap">{{ campanhaDetalhes.mensagem }}</p>
            </div>
          </div>

          <!-- Aba: Logs -->
          <div v-else class="flex-1 overflow-y-auto p-4 space-y-2 min-h-0">
            <div v-if="carregandoLogs" class="flex items-center justify-center py-10 text-muted-foreground text-sm gap-2">
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Carregando logs...
            </div>
            <div v-else-if="logs.length === 0" class="text-center py-10 text-muted-foreground text-sm">
              Nenhum log registrado para esta campanha.
            </div>
            <div v-else class="space-y-1.5">
              <div
                v-for="log in logs"
                :key="log.id"
                :class="[
                  'flex gap-3 rounded-lg p-3 text-xs border',
                  log.nivel === 'erro'  ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' :
                  log.nivel === 'aviso' ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800' :
                                          'bg-muted/30 border-border'
                ]"
              >
                <!-- Ícone do nível -->
                <span class="shrink-0 mt-0.5">
                  <svg v-if="log.nivel === 'erro'"  class="w-3.5 h-3.5 text-red-500"   fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
                  <svg v-else-if="log.nivel === 'aviso'" class="w-3.5 h-3.5 text-amber-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                  <svg v-else class="w-3.5 h-3.5 text-primary" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                </span>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between gap-2">
                    <span :class="['font-medium', log.nivel === 'erro' ? 'text-red-700 dark:text-red-400' : log.nivel === 'aviso' ? 'text-amber-700 dark:text-amber-400' : 'text-foreground']">
                      {{ log.evento }}
                    </span>
                    <span class="text-muted-foreground shrink-0">
                      {{ new Date(log.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }) }}
                    </span>
                  </div>
                  <p v-if="log.detalhe" class="text-muted-foreground mt-0.5 break-words">{{ log.detalhe }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Modal de confirmação genérico -->
    <ConfirmModal
      :show="confirmModal.show"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :loading="confirmModal.loading"
      confirm-text="Excluir"
      variant="danger"
      @confirm="executarConfirm"
      @cancel="confirmModal.show = false"
    />

    <!-- Modal: canais insuficientes para multi-canal -->
    <Teleport to="body">
      <div v-if="modalCanaisInsuficientes.show" class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div class="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl p-6">
          <div class="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-amber-100 dark:bg-amber-900/20 rounded-full">
            <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-foreground text-center mb-2">Conecte mais números</h3>
          <p class="text-sm text-muted-foreground text-center mb-1">
            Para usar <strong class="text-foreground">{{ modalCanaisInsuficientes.recurso }}</strong> é preciso ter pelo menos
            <strong class="text-foreground">2 canais conectados</strong>.
          </p>
          <p class="text-sm text-muted-foreground text-center mb-6">
            Você tem <strong :class="canaisConectados.length === 0 ? 'text-red-500' : 'text-amber-600'">{{ canaisConectados.length }}</strong> canal(is) conectado(s) no momento.
            Crie novos canais e conecte os números na aba <strong class="text-foreground">Configurações</strong>.
          </p>
          <div class="flex gap-3">
            <button
              @click="modalCanaisInsuficientes.show = false"
              class="flex-1 px-4 py-2 border border-border rounded-lg text-sm text-foreground hover:bg-muted transition"
            >
              Entendi
            </button>
            <NuxtLink
              to="/configuracoes"
              class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition text-center"
            >
              Ir para Configurações
            </NuxtLink>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
