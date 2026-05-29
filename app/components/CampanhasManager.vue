<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCampanhas } from '~/composables/useCampanhas'
import { usePublicos } from '~/composables/usePublicos'
import { useCanais } from '~/composables/useCanais'
import type { Campanha } from '~/composables/useCampanhas'

const { campanhas, isLoading, fetchCampanhas, criarCampanha, atualizarStatus, excluirCampanha } = useCampanhas()
const { publicos, fetchPublicos } = usePublicos()
const { canais, fetchCanais } = useCanais()

let toast: any
onMounted(async () => {
  toast = await useToastSafe()
  await Promise.all([fetchCampanhas(), fetchPublicos(), fetchCanais()])
})

const canaisConectados = computed(() => canais.value.filter((c) => c.status === 'conectado'))

// ── Modal Criar Campanha ─────────────────────────────────────────────────────
const showModalCriar = ref(false)
const criando = ref(false)
const form = ref({
  nome: '',
  publico_id: '',
  canal_id: '',
  modo_mensagem: 'manual' as 'manual' | 'ia',
  mensagem: '',
  intervalo_segundos: 10
})

function abrirModalCriar() {
  form.value = { nome: '', publico_id: '', canal_id: '', modo_mensagem: 'manual', mensagem: '', intervalo_segundos: 10 }
  showModalCriar.value = true
}

const publicoSelecionado = computed(() =>
  publicos.value.find((p) => p.id === form.value.publico_id)
)

const formValido = computed(() => {
  if (!form.value.nome || !form.value.publico_id || !form.value.canal_id) return false
  // No modo manual a mensagem é obrigatória; no modo IA ela é gerada a partir da observação
  if (form.value.modo_mensagem === 'manual' && !form.value.mensagem) return false
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
      canal_id: form.value.canal_id,
      modo_mensagem: form.value.modo_mensagem,
      mensagem: form.value.modo_mensagem === 'manual' ? form.value.mensagem : null,
      intervalo_segundos: form.value.intervalo_segundos
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

function iniciarDisparo(campanha: Campanha) {
  if (!campanha.canal_id) {
    toast?.error('Esta campanha não tem canal vinculado')
    return
  }
  const canal = canais.value.find((c) => c.id === campanha.canal_id)
  if (!canal || canal.status !== 'conectado') {
    toast?.error('O canal vinculado não está conectado. Verifique em Configurações.')
    return
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
    // O ai-service atualiza status e métricas no banco; recarrega a lista (agora e em seguida).
    await fetchCampanhas()
    setTimeout(fetchCampanhas, 2500)
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
    message: `Deseja realmente excluir a campanha "${campanha.nome}"? Esta ação não pode ser desfeita.`,
    onConfirm: async () => {
      try {
        await excluirCampanha(campanha.id)
        toast?.success('Campanha excluída')
      } catch {
        toast?.error('Erro ao excluir')
        throw new Error()
      }
    }
  }
}

// ── Modal Detalhes ────────────────────────────────────────────────────────────
const showModalDetalhes = ref(false)
const campanhaDetalhes = ref<Campanha | null>(null)

function verDetalhes(c: Campanha) {
  campanhaDetalhes.value = c
  showModalDetalhes.value = true
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
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold text-foreground">Campanhas</h2>
        <p class="text-sm text-muted-foreground">Crie e gerencie disparos em massa via WhatsApp</p>
      </div>
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
              <span :class="['text-xs px-2 py-0.5 rounded-full font-medium shrink-0', statusConfig[c.status]?.color]">
                {{ statusConfig[c.status]?.label }}
              </span>
            </div>
            <p class="text-sm text-muted-foreground">
              Público: <span class="text-foreground">{{ (c as any).publico?.nome || '—' }}</span>
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
            <div v-if="c.total_enviados + c.total_falhas > 0">
              <p class="text-lg font-bold text-primary">{{ taxaEnvio(c) }}%</p>
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
            :disabled="campanhaEmDisparo !== null"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50"
          >
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            Disparar
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
        <div class="bg-card border border-border rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl">
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

            <div>
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
          <div class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-xs text-amber-700 dark:text-amber-400">
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
        <div class="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl">
          <div class="flex items-center justify-between p-6 border-b border-border">
            <h3 class="text-lg font-semibold">{{ campanhaDetalhes.nome }}</h3>
            <button @click="showModalDetalhes = false" class="text-muted-foreground hover:text-foreground">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
          <div class="p-6 space-y-4">
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
                <span class="text-muted-foreground">Criada em</span>
                <span class="text-foreground">{{ new Date(campanhaDetalhes.created_at).toLocaleDateString('pt-BR') }}</span>
              </div>
              <div v-if="campanhaDetalhes.iniciado_em" class="flex justify-between">
                <span class="text-muted-foreground">Iniciada em</span>
                <span class="text-foreground">{{ new Date(campanhaDetalhes.iniciado_em).toLocaleString('pt-BR') }}</span>
              </div>
            </div>
            <div class="p-3 bg-muted/30 rounded-lg">
              <p class="text-xs text-muted-foreground mb-1">Mensagem</p>
              <p class="text-sm text-foreground whitespace-pre-wrap">{{ campanhaDetalhes.mensagem }}</p>
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
  </div>
</template>
