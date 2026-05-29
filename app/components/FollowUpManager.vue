<template>
  <div class="space-y-6">
    <!-- Barra superior: filtro por campanha + nova sequência -->
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div class="flex flex-col gap-1">
        <label class="text-xs font-medium text-muted-foreground">Visualizar analítica de</label>
        <select
          v-model="filtroCampanha"
          @change="aplicarFiltro"
          class="min-w-[260px] text-sm border border-border rounded-lg px-3 py-2 bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
        >
          <option value="__all__">Todas as campanhas</option>
          <option v-for="c in campanhas" :key="c.id" :value="c.id">{{ c.nome }}</option>
        </select>
      </div>
      <button
        @click="abrirModalCriar"
        class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition text-sm font-medium"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Nova Sequência
      </button>
    </div>

    <!-- Métricas (filtradas) -->
    <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="bg-card border border-border rounded-xl p-4">
        <p class="text-2xl font-bold tabular-nums text-foreground">{{ metricas.total }}</p>
        <p class="text-xs text-muted-foreground mt-1">Total na cadência</p>
      </div>
      <div class="bg-card border border-green-800/20 bg-green-950/5 rounded-xl p-4">
        <p class="text-2xl font-bold tabular-nums text-green-500">{{ metricas.enviados }}</p>
        <p class="text-xs text-muted-foreground mt-1">Enviados</p>
      </div>
      <div class="bg-card border border-primary/20 bg-primary/5 rounded-xl p-4">
        <p class="text-2xl font-bold tabular-nums text-primary">{{ metricas.responderam }}</p>
        <p class="text-xs text-muted-foreground mt-1">Responderam</p>
      </div>
      <div class="bg-card border border-amber-800/20 bg-amber-950/5 rounded-xl p-4">
        <p class="text-2xl font-bold tabular-nums text-amber-500">{{ metricas.pendentes }}</p>
        <p class="text-xs text-muted-foreground mt-1">Pendentes</p>
      </div>
      <div class="bg-card border border-border rounded-xl p-4">
        <p class="text-2xl font-bold tabular-nums text-muted-foreground">{{ metricas.cancelados }}</p>
        <p class="text-xs text-muted-foreground mt-1">Encerrados</p>
      </div>
    </div>

    <!-- Sequências configuradas -->
    <div>
      <h3 class="text-sm font-semibold text-foreground mb-3">Sequências configuradas</h3>

      <div v-if="isLoading" class="space-y-3">
        <div v-for="i in 2" :key="i" class="h-24 bg-card rounded-xl border border-border animate-pulse"/>
      </div>

      <div v-else-if="configs.length === 0" class="text-center py-12 bg-card rounded-xl border border-border">
        <svg class="w-10 h-10 mx-auto text-muted-foreground/30 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        <p class="text-muted-foreground font-medium">Nenhuma sequência de follow-up</p>
        <p class="text-xs text-muted-foreground mt-1">Crie uma sequência global ou para uma campanha específica.</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="cfg in configs"
          :key="cfg.id"
          class="bg-card border border-border rounded-xl overflow-hidden hover:border-primary/30 transition"
        >
          <div class="flex items-start justify-between gap-4 p-5">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <h3 class="font-semibold text-foreground truncate">
                  {{ cfg.campanha?.nome || 'Todas as campanhas' }}
                </h3>
                <span v-if="!cfg.campanha_id" class="text-xs px-2 py-0.5 rounded-full font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 shrink-0">
                  Global
                </span>
                <span :class="cfg.ativo ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-muted text-muted-foreground'"
                  class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0">
                  {{ cfg.ativo ? 'Ativa' : 'Pausada' }}
                </span>
              </div>
              <p class="text-xs text-muted-foreground">{{ cfg.etapas.length }} etapa(s)</p>
            </div>
          </div>

          <!-- Etapas -->
          <div class="px-5 pb-3">
            <div class="flex items-center gap-2 overflow-x-auto pb-1">
              <div v-for="(etapa, idx) in cfg.etapas" :key="etapa.id || idx" class="flex items-center gap-2 shrink-0">
                <div class="flex items-center gap-2 bg-muted/40 border border-border rounded-lg px-3 py-2 text-xs">
                  <span class="w-5 h-5 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center text-[10px]">{{ etapa.ordem }}</span>
                  <span class="text-muted-foreground">{{ formatDelay(etapa.delay_minutos) }}</span>
                  <span :class="etapa.modo_mensagem === 'ia' ? 'text-purple-600 dark:text-purple-400' : 'text-foreground'" class="font-medium">
                    {{ etapa.modo_mensagem === 'ia' ? '✨ IA' : '✏️ Manual' }}
                  </span>
                </div>
                <svg v-if="idx < cfg.etapas.length - 1" class="w-4 h-4 text-muted-foreground shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </div>
            </div>
          </div>

          <!-- Ações -->
          <div class="flex items-center gap-2 px-5 py-3 border-t border-border">
            <button @click="toggle(cfg.id, !cfg.ativo)" class="px-3 py-1.5 text-xs font-medium border border-border rounded-lg text-foreground hover:bg-muted transition">
              {{ cfg.ativo ? 'Pausar' : 'Ativar' }}
            </button>
            <button @click="abrirEditar(cfg)" class="px-3 py-1.5 text-xs font-medium border border-border rounded-lg text-foreground hover:bg-muted transition">
              Editar
            </button>
            <button @click="confirmarRemover(cfg)" class="ml-auto p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Histórico / Logs -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-foreground">Histórico de follow-ups</h3>
        <button @click="aplicarFiltro" class="text-xs text-primary hover:underline flex items-center gap-1">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
          Atualizar
        </button>
      </div>

      <div class="bg-card border border-border rounded-xl overflow-hidden">
        <div v-if="historico.length === 0" class="text-center py-10 text-muted-foreground text-sm">
          Nenhum follow-up registrado ainda{{ filtroCampanha !== '__all__' ? ' para esta campanha' : '' }}.
        </div>
        <div v-else class="overflow-x-auto" style="max-height: 460px; overflow-y: auto;">
          <table class="w-full text-sm">
            <thead class="bg-muted sticky top-0 z-10 border-b border-border">
              <tr>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Contato</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Campanha</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Etapa</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Status</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs min-w-[220px]">Mensagem</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Quando</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="h in historico" :key="h.id" class="border-b border-border/50 hover:bg-muted/30 transition-colors align-top">
                <td class="py-3 px-3 font-medium text-foreground whitespace-nowrap">{{ h.contato?.nome || '—' }}</td>
                <td class="py-3 px-3 text-muted-foreground whitespace-nowrap">{{ h.campanha?.nome || '—' }}</td>
                <td class="py-3 px-3 text-muted-foreground whitespace-nowrap">{{ h.etapa?.ordem ?? '—' }}ª</td>
                <td class="py-3 px-3 whitespace-nowrap">
                  <span :class="['inline-flex px-2 py-0.5 rounded-full text-xs font-medium', statusClasse(h.status)]">{{ statusLabel(h.status) }}</span>
                </td>
                <td class="py-3 px-3 text-foreground text-xs">{{ h.mensagem_enviada || '—' }}</td>
                <td class="py-3 px-3 text-muted-foreground text-xs whitespace-nowrap">{{ formatarData(h.enviado_em || h.agendado_para) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Modal Criar/Editar ── -->
    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div class="bg-card border border-border rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
          <div class="flex items-center justify-between p-6 border-b border-border">
            <h3 class="text-lg font-semibold">{{ editingId ? 'Editar' : 'Nova' }} Sequência de Follow-up</h3>
            <button @click="showModal = false" class="text-muted-foreground hover:text-foreground">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <div class="p-6 space-y-5">
            <!-- Escopo -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Aplicar a <span class="text-red-500">*</span></label>
              <select v-model="form.campanha_id" class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
                <option value="__all__">Todas as campanhas (global)</option>
                <option v-for="c in campanhas" :key="c.id" :value="c.id">{{ c.nome }} ({{ c.total_enviados }} enviados)</option>
              </select>
              <p class="text-xs text-muted-foreground mt-1">
                {{ form.campanha_id === '__all__'
                  ? 'Vale para todas as campanhas que não tenham uma sequência própria.'
                  : 'Sequência exclusiva desta campanha (tem prioridade sobre a global).' }}
              </p>
            </div>

            <!-- Etapas -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-sm font-medium text-foreground">Etapas de Follow-up</label>
                <button @click="addEtapa" class="text-xs text-primary hover:underline flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                  Adicionar etapa
                </button>
              </div>
              <div class="space-y-3">
                <div v-for="(etapa, idx) in form.etapas" :key="idx" class="border border-border rounded-xl p-4 space-y-3">
                  <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold text-muted-foreground">Etapa {{ idx + 1 }}</span>
                    <button v-if="form.etapas.length > 1" @click="removeEtapa(idx)" class="text-red-500 hover:text-red-600 transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-foreground mb-1">Aguardar antes de enviar</label>
                    <div class="flex gap-2">
                      <input v-model.number="etapa.delay_valor" type="number" min="1" class="w-24 px-3 py-1.5 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
                      <select v-model="etapa.delay_unidade" class="flex-1 px-3 py-1.5 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
                        <option value="minutos">Minutos</option>
                        <option value="horas">Horas</option>
                        <option value="dias">Dias</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-foreground mb-1">Mensagem</label>
                    <div class="grid grid-cols-2 gap-2">
                      <button type="button" @click="etapa.modo_mensagem = 'ia'"
                        :class="['flex flex-col items-start gap-0.5 rounded-lg border p-2.5 text-left transition text-xs', etapa.modo_mensagem === 'ia' ? 'border-primary bg-primary/5 ring-1 ring-primary/40' : 'border-border hover:border-primary/30']">
                        <span class="font-medium text-foreground">✨ IA</span>
                        <span class="text-muted-foreground">Gerada pelo contexto</span>
                      </button>
                      <button type="button" @click="etapa.modo_mensagem = 'manual'"
                        :class="['flex flex-col items-start gap-0.5 rounded-lg border p-2.5 text-left transition text-xs', etapa.modo_mensagem === 'manual' ? 'border-primary bg-primary/5 ring-1 ring-primary/40' : 'border-border hover:border-primary/30']">
                        <span class="font-medium text-foreground">✏️ Manual</span>
                        <span class="text-muted-foreground">Você escreve</span>
                      </button>
                    </div>
                    <textarea v-if="etapa.modo_mensagem === 'manual'" v-model="etapa.mensagem" rows="3"
                      placeholder="Oi {nome}, só passando para ver se ficou alguma dúvida..."
                      class="w-full mt-2 px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
                    <p v-if="etapa.modo_mensagem === 'ia'" class="text-xs text-muted-foreground mt-1.5">
                      A IA usa o contexto da última mensagem enviada (inclusive as manuais) para gerar este follow-up.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="flex gap-3 p-6 border-t border-border">
            <button @click="showModal = false" class="flex-1 px-4 py-2 border border-border rounded-lg text-sm text-foreground hover:bg-muted transition">Cancelar</button>
            <button @click="salvar" :disabled="salvando || form.etapas.length === 0"
              class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50">
              {{ salvando ? 'Salvando...' : 'Salvar Sequência' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <ConfirmModal
      :show="!!cfgParaRemover"
      title="Remover Sequência"
      :message="`Remover a sequência ${cfgParaRemover?.campanha?.nome ? 'da campanha ' + cfgParaRemover.campanha.nome : 'global'}? Nenhum novo follow-up será agendado.`"
      confirm-text="Remover"
      variant="danger"
      @confirm="excluir"
      @cancel="cfgParaRemover = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCampanhas } from '~/composables/useCampanhas'
import type { FollowUpConfig } from '~/composables/useFollowUps'

const { configs, metricas, historico, isLoading, fetchConfigs, fetchAnalytics, criar, remover, toggleAtivo } = useFollowUps()
const { campanhas, fetchCampanhas } = useCampanhas()

let toast: any
const filtroCampanha = ref('__all__')

onMounted(async () => {
  toast = await useToastSafe()
  await Promise.all([fetchConfigs(), fetchCampanhas(), fetchAnalytics()])
})

function aplicarFiltro() {
  fetchAnalytics(filtroCampanha.value)
}

// ── Modal ─────────────────────────────────────────────────────────────────────
const showModal = ref(false)
const editingId = ref<string | null>(null)
const salvando = ref(false)

interface EtapaForm {
  delay_valor: number
  delay_unidade: 'minutos' | 'horas' | 'dias'
  modo_mensagem: 'ia' | 'manual'
  mensagem: string
}

const form = ref<{ campanha_id: string; etapas: EtapaForm[] }>({
  campanha_id: '__all__',
  etapas: [{ delay_valor: 1, delay_unidade: 'horas', modo_mensagem: 'ia', mensagem: '' }]
})

function etapaToMinutos(e: EtapaForm): number {
  const m = { minutos: 1, horas: 60, dias: 1440 }
  return e.delay_valor * m[e.delay_unidade]
}

function minutosToEtapa(min: number): { delay_valor: number; delay_unidade: 'minutos' | 'horas' | 'dias' } {
  if (min % 1440 === 0) return { delay_valor: min / 1440, delay_unidade: 'dias' }
  if (min % 60 === 0) return { delay_valor: min / 60, delay_unidade: 'horas' }
  return { delay_valor: min, delay_unidade: 'minutos' }
}

function abrirModalCriar() {
  editingId.value = null
  form.value = { campanha_id: '__all__', etapas: [{ delay_valor: 1, delay_unidade: 'horas', modo_mensagem: 'ia', mensagem: '' }] }
  showModal.value = true
}

function abrirEditar(cfg: FollowUpConfig) {
  editingId.value = cfg.id
  form.value = {
    campanha_id: cfg.campanha_id || '__all__',
    etapas: cfg.etapas.map(e => ({
      ...minutosToEtapa(e.delay_minutos),
      modo_mensagem: e.modo_mensagem as 'ia' | 'manual',
      mensagem: e.mensagem || ''
    }))
  }
  showModal.value = true
}

function addEtapa() {
  form.value.etapas.push({ delay_valor: 1, delay_unidade: 'dias', modo_mensagem: 'ia', mensagem: '' })
}

function removeEtapa(idx: number) {
  form.value.etapas.splice(idx, 1)
}

async function salvar() {
  salvando.value = true
  try {
    await criar({
      campanha_id: form.value.campanha_id === '__all__' ? null : form.value.campanha_id,
      etapas: form.value.etapas.map((e, i) => ({
        ordem: i + 1,
        delay_minutos: etapaToMinutos(e),
        modo_mensagem: e.modo_mensagem,
        mensagem: e.modo_mensagem === 'manual' ? e.mensagem : null
      }))
    })
    showModal.value = false
    toast?.success('Sequência salva!')
    await fetchAnalytics(filtroCampanha.value)
  } catch (e: any) {
    toast?.error(e.message || 'Erro ao salvar')
  } finally {
    salvando.value = false
  }
}

async function toggle(id: string, ativo: boolean) {
  try { await toggleAtivo(id, ativo); toast?.success(ativo ? 'Sequência ativada' : 'Sequência pausada') }
  catch { toast?.error('Erro ao alterar') }
}

const cfgParaRemover = ref<FollowUpConfig | null>(null)
function confirmarRemover(cfg: FollowUpConfig) { cfgParaRemover.value = cfg }
async function excluir() {
  if (!cfgParaRemover.value) return
  try {
    await remover(cfgParaRemover.value.id)
    cfgParaRemover.value = null
    toast?.success('Sequência removida')
  } catch { toast?.error('Erro ao remover') }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDelay(min: number): string {
  if (min >= 1440) return `${min / 1440}d`
  if (min >= 60) return `${min / 60}h`
  return `${min}min`
}

function formatarData(d: string | null): string {
  if (!d) return '—'
  return new Date(d).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const statusLabels: Record<string, string> = {
  pendente: 'Pendente', enviado: 'Enviado', respondeu: 'Respondeu', cancelado: 'Encerrado'
}
function statusLabel(s: string) { return statusLabels[s] || s }

function statusClasse(s: string): string {
  if (s === 'respondeu') return 'bg-primary/10 text-primary'
  if (s === 'enviado') return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
  if (s === 'pendente') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
  return 'bg-muted text-muted-foreground'
}
</script>
