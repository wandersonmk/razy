<template>
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Abas + ações, na mesma linha -->
    <div class="flex items-center justify-between border-b border-border px-6 flex-wrap gap-3">
      <div class="flex">
        <button @click="abaAtiva = 'disparos'"
          :class="['py-3 px-1 mr-6 text-sm font-medium border-b-2 transition', abaAtiva === 'disparos' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']">
          Disparos
        </button>
        <button @click="abaAtiva = 'atendimento'"
          :class="['py-3 px-1 mr-6 text-sm font-medium border-b-2 transition', abaAtiva === 'atendimento' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']">
          Atendimento
        </button>
        <button @click="abaAtiva = 'ranking'"
          :class="['py-3 px-1 text-sm font-medium border-b-2 transition flex items-center gap-1', abaAtiva === 'ranking' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']">
          🏆 Ranking
        </button>
      </div>

      <div v-if="abaAtiva === 'disparos'" class="flex items-center gap-3 py-2">
        <button
          @click="atualizar"
          :disabled="isLoading"
          class="flex items-center justify-center gap-2 px-4 py-2 border border-border hover:bg-muted disabled:opacity-50 text-foreground rounded-lg transition-colors text-sm font-medium"
          title="Atualizar respostas"
        >
          <svg :class="['w-4 h-4', isLoading ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          <span>Atualizar</span>
          <span v-if="ultimaAtualizacao" class="text-xs text-muted-foreground font-normal hidden sm:inline">· {{ ultimaAtualizacao }}</span>
        </button>
        <button
          @click="exportToPDF"
          :disabled="relatoriosFiltrados.length === 0"
          class="flex items-center justify-center gap-2 w-36 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg transition-colors text-sm font-medium"
          title="Exportar para PDF"
        >
          <Icon icon="file-pdf" class-name="w-4 h-4" fallback="" />
          <span>Exportar PDF</span>
        </button>
        <button
          @click="exportToExcel"
          :disabled="relatoriosFiltrados.length === 0"
          class="flex items-center justify-center gap-2 w-36 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg transition-colors text-sm font-medium"
          title="Exportar para Excel"
        >
          <Icon icon="file-excel" class-name="w-4 h-4" fallback="" />
          <span>Exportar Excel</span>
        </button>
      </div>
    </div>

    <RelatorioAtendimento v-if="abaAtiva === 'atendimento'" />
    <RankingAtendimento v-else-if="abaAtiva === 'ranking'" />

    <template v-else>
    <!-- Cards de métricas -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 p-6 border-b border-border">
      <div class="rounded-xl border border-border p-4">
        <p class="text-2xl font-bold tabular-nums text-foreground">{{ metricas.total.toLocaleString('pt-BR') }}</p>
        <p class="text-xs text-muted-foreground mt-1">Total de disparos</p>
      </div>
      <div class="rounded-xl border border-green-800/20 bg-green-950/5 p-4">
        <p class="text-2xl font-bold tabular-nums text-green-500">{{ metricas.enviados.toLocaleString('pt-BR') }}</p>
        <p class="text-xs text-muted-foreground mt-1">Enviados</p>
      </div>
      <div class="rounded-xl border border-red-800/20 bg-red-950/5 p-4">
        <p class="text-2xl font-bold tabular-nums text-red-500">{{ metricas.falhas.toLocaleString('pt-BR') }}</p>
        <p class="text-xs text-muted-foreground mt-1">Falhas</p>
      </div>
      <div class="rounded-xl border border-primary/20 bg-primary/5 p-4">
        <p class="text-2xl font-bold tabular-nums text-primary">{{ metricas.respostas.toLocaleString('pt-BR') }}</p>
        <p class="text-xs text-muted-foreground mt-1">Respostas</p>
      </div>
    </div>

    <!-- Filtros -->
    <div class="p-6 border-b border-border bg-muted/30">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-foreground mb-2">Buscar (nome ou telefone)</label>
          <input
            v-model="filtros.busca"
            type="text"
            placeholder="Digite nome ou telefone"
            class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-2">Campanha</label>
          <select
            v-model="filtros.campanha"
            class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <option value="">Todas</option>
            <option v-for="c in campanhasDisponiveis" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-foreground mb-2">Status</label>
          <select
            v-model="filtros.status"
            class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <option value="">Todos</option>
            <option value="enviado">Enviados</option>
            <option value="falhou">Falhas</option>
            <option value="respondido">Respondidos</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Conteúdo -->
    <div class="p-6">
      <div v-if="isLoading" class="text-center py-10 text-muted-foreground">Carregando relatórios...</div>

      <div v-else-if="error" class="text-center py-10">
        <p class="text-muted-foreground mb-4">{{ error }}</p>
        <button @click="recarregar" class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition">
          Tentar novamente
        </button>
      </div>

      <div v-else-if="relatoriosFiltrados.length === 0" class="text-center py-10">
        <Icon icon="file-alt" class-name="w-12 h-12 text-muted-foreground/40 mb-4 mx-auto" fallback="" />
        <h3 class="text-lg font-medium text-foreground mb-1">Nenhum disparo encontrado</h3>
        <p class="text-muted-foreground text-sm">Os disparos das campanhas aparecem aqui conforme são enviados.</p>
      </div>

      <div v-else class="overflow-x-auto">
        <div style="max-height: 560px; overflow-y: auto;">
          <table class="w-full text-sm">
            <thead class="bg-muted sticky top-0 z-10 border-b border-border">
              <tr>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs whitespace-nowrap">Contato</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs whitespace-nowrap">Telefone</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs whitespace-nowrap">Campanha</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs whitespace-nowrap">Canal</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs whitespace-nowrap">Status</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs min-w-[260px]">Mensagem</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs min-w-[220px]">Resposta</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs whitespace-nowrap">Data</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in relatoriosFiltrados.slice(0, visiveis)"
                :key="r.id"
                class="border-b border-border/50 hover:bg-muted/30 transition-colors align-top"
              >
                <td class="py-3 px-3 font-medium text-foreground whitespace-nowrap">{{ r.contato_nome }}</td>
                <td class="py-3 px-3 text-foreground font-mono text-xs whitespace-nowrap">{{ r.telefone }}</td>
                <td class="py-3 px-3 text-muted-foreground whitespace-nowrap">{{ r.campanha_nome }}</td>
                <td class="py-3 px-3 text-foreground font-mono text-xs whitespace-nowrap">{{ r.canal_telefone || '—' }}</td>
                <td class="py-3 px-3 whitespace-nowrap">
                  <span :class="['inline-flex px-2 py-0.5 rounded-full text-xs font-medium', statusClasse(r)]">
                    {{ statusLabel(r) }}
                  </span>
                </td>
                <td class="py-3 px-3 text-foreground text-xs">{{ r.mensagem_enviada || '—' }}</td>
                <td class="py-3 px-3 text-xs" :class="r.resposta_texto ? 'text-foreground' : 'text-muted-foreground'">
                  {{ r.resposta_texto || '—' }}
                </td>
                <td class="py-3 px-3 text-muted-foreground text-xs whitespace-nowrap">{{ formatarData(r.enviado_em || r.created_at) }}</td>
              </tr>
              <tr v-if="visiveis < relatoriosFiltrados.length">
                <td :colspan="8"><div ref="sentinel" style="height:1px;"/></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import type { DisparoRelatorio } from '~/composables/useRelatorios'

// Permite abrir direto numa aba via /relatorios?aba=ranking (usado pelo link
// "Ver ranking completo" do Dashboard) — e mantém a URL em sincronia ao trocar
// de aba, porque é dali que o layout (dashboard.vue) lê o título/descrição do
// cabeçalho da página.
const route = useRoute()
const router = useRouter()
const abaInicial = (route.query.aba === 'ranking' || route.query.aba === 'atendimento') ? route.query.aba : 'disparos'
const abaAtiva = ref<'disparos' | 'atendimento' | 'ranking'>(abaInicial)

watch(abaAtiva, (val) => {
  if (route.query.aba === val) return
  router.replace({ query: { ...route.query, aba: val } })
})

const { relatorios, metricas, isLoading, error, fetchRelatorios, clearError } = useRelatorios()

const filtros = ref({ busca: '', campanha: '', status: '' })
const visiveis = ref(20)
const sentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

// Atualização manual (evita polling pesado com muitos leads)
const ultimaAtualizacao = ref<string>('')

function marcarAtualizacao() {
  ultimaAtualizacao.value = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

async function atualizar() {
  await fetchRelatorios()
  marcarAtualizacao()
}

onMounted(async () => {
  await fetchRelatorios()
  marcarAtualizacao()
  nextTick(setupInfiniteScroll)
})

const campanhasDisponiveis = computed(() => {
  const set = new Set<string>()
  for (const r of relatorios.value) if (r.campanha_nome) set.add(r.campanha_nome)
  return [...set].sort()
})

const relatoriosFiltrados = computed(() => {
  const termo = filtros.value.busca.trim().toLowerCase()
  return relatorios.value.filter((r) => {
    if (filtros.value.campanha && r.campanha_nome !== filtros.value.campanha) return false
    if (filtros.value.status === 'respondido' && !r.respondido_em) return false
    if (filtros.value.status && filtros.value.status !== 'respondido' && r.status !== filtros.value.status) return false
    if (termo) {
      const alvo = `${r.contato_nome} ${r.telefone}`.toLowerCase()
      if (!alvo.includes(termo)) return false
    }
    return true
  })
})

function statusLabel(r: DisparoRelatorio): string {
  if (r.respondido_em) return 'Respondeu'
  return { enviado: 'Enviado', falhou: 'Falhou', pendente: 'Pendente' }[r.status] || r.status
}

function statusClasse(r: DisparoRelatorio): string {
  if (r.respondido_em) return 'bg-primary/10 text-primary'
  if (r.status === 'enviado') return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
  if (r.status === 'falhou') return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
  return 'bg-muted text-muted-foreground'
}

function formatarData(d: string | null): string {
  if (!d) return '—'
  return new Date(d).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function recarregar() {
  clearError()
  fetchRelatorios()
}

function setupInfiniteScroll() {
  if (observer) { observer.disconnect(); observer = null }
  if (sentinel.value && relatoriosFiltrados.value.length > visiveis.value) {
    observer = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting && visiveis.value < relatoriosFiltrados.value.length) {
        visiveis.value += 20
      }
    })
    observer.observe(sentinel.value)
  }
}

watch(() => relatoriosFiltrados.value.length, () => { visiveis.value = 20; nextTick(setupInfiniteScroll) })

// Remove emojis/símbolos não suportados pela fonte Latin-1 do jsPDF (mantém acentos).
function pdfSafe(s: string | null | undefined): string {
  return (s || '')
    .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE00}-\u{FE0F}\u{2190}-\u{21FF}\u{2300}-\u{23FF}]/gu, '')
    .replace(/[^\x00-\xFF]/g, '')
    .trim()
}

async function exportToPDF() {
  if (typeof window === 'undefined') return
  try {
    const { jsPDF } = await import('jspdf')
    const doc = new jsPDF({ orientation: 'landscape' })
    const agora = new Date()

    // Header roxo
    doc.setFillColor(102, 90, 228)
    doc.rect(0, 0, 297, 45, 'F')
    doc.setTextColor(255, 255, 255)
    doc.setFontSize(24)
    doc.setFont('helvetica', 'bold')
    doc.text('Razy', 20, 20)
    doc.setFontSize(14)
    doc.setFont('helvetica', 'normal')
    doc.text('Relatório de Disparos', 20, 35)

    doc.setTextColor(0, 0, 0)
    doc.setFontSize(10)
    doc.text(`Gerado em: ${agora.toLocaleString('pt-BR')}`, 20, 58)
    doc.text(`Total: ${relatoriosFiltrados.value.length} registros`, 20, 66)

    // Layout: margem esquerda=12, margem direita=12 → largura útil=273mm (x=12..285)
    // Colunas: Contato Telefone Campanha Canal Status Resposta Data
    const COL = { contato: 14, telefone: 50, campanha: 88, canal: 124, status: 158, resposta: 186, data: 250 }
    const TABLE_X = 12
    const TABLE_W = 273

    const drawHeader = (yPos: number) => {
      doc.setFillColor(102, 90, 228)
      doc.rect(TABLE_X, yPos - 10, TABLE_W, 15, 'F')
      doc.setTextColor(255, 255, 255)
      doc.setFontSize(10)
      doc.setFont('helvetica', 'bold')
      doc.text('Contato',   COL.contato,   yPos - 2)
      doc.text('Telefone',  COL.telefone,  yPos - 2)
      doc.text('Campanha',  COL.campanha,  yPos - 2)
      doc.text('Canal',     COL.canal,     yPos - 2)
      doc.text('Status',    COL.status,    yPos - 2)
      doc.text('Resposta',  COL.resposta,  yPos - 2)
      doc.text('Data',      COL.data,      yPos - 2)
      doc.setTextColor(0, 0, 0)
      doc.setFontSize(9)
      doc.setFont('helvetica', 'normal')
    }

    let y = 80
    drawHeader(y)
    y += 10

    relatoriosFiltrados.value.forEach((r, index) => {
      if (y > 185) {
        doc.addPage()
        y = 20
        drawHeader(y)
        y += 10
      }
      if (index % 2 === 0) {
        doc.setFillColor(249, 250, 251)
        doc.rect(TABLE_X, y - 7, TABLE_W, 11, 'F')
      }
      doc.text(pdfSafe(r.contato_nome).substring(0, 16) || '—', COL.contato,  y)
      doc.text((r.telefone      || '—').substring(0, 14), COL.telefone, y)
      doc.text(pdfSafe(r.campanha_nome).substring(0, 15) || '—', COL.campanha, y)
      doc.text((r.canal_telefone || '—').substring(0, 14), COL.canal,   y)
      doc.text(statusLabel(r).substring(0, 10),           COL.status,   y)
      doc.text(pdfSafe(r.resposta_texto).substring(0, 26) || '—', COL.resposta, y)
      doc.text(formatarData(r.enviado_em || r.created_at),COL.data,     y)
      y += 12
    })

    doc.save(`relatorio-disparos-${agora.toISOString().split('T')[0]}.pdf`)
  } catch (e) {
    console.error('Erro ao exportar PDF:', e)
    alert('Erro ao exportar PDF. Tente novamente.')
  }
}

async function exportToExcel() {
  if (typeof window === 'undefined') return
  try {
    const XLSX = await import('xlsx')
    const agora = new Date()
    const linhas: any[][] = [
      ['Razy - Relatório de Disparos'],
      [`Gerado em: ${agora.toLocaleString('pt-BR')}`],
      [`Total: ${relatoriosFiltrados.value.length} registros`],
      [],
      ['#', 'Contato', 'Telefone', 'Campanha', 'Canal', 'Status', 'Mensagem', 'Resposta', 'Data']
    ]
    relatoriosFiltrados.value.forEach((r, i) => {
      linhas.push([
        (i + 1).toString(),
        r.contato_nome,
        r.telefone,
        r.campanha_nome,
        r.canal_telefone || '',
        statusLabel(r),
        r.mensagem_enviada || '',
        r.resposta_texto || '',
        formatarData(r.enviado_em || r.created_at)
      ])
    })
    const wb = XLSX.utils.book_new()
    const ws = XLSX.utils.aoa_to_sheet(linhas)
    ws['!cols'] = [{ wch: 5 }, { wch: 24 }, { wch: 16 }, { wch: 22 }, { wch: 16 }, { wch: 12 }, { wch: 40 }, { wch: 40 }, { wch: 18 }]
    XLSX.utils.book_append_sheet(wb, ws, 'Disparos')
    XLSX.writeFile(wb, `relatorio-disparos-${agora.toISOString().split('T')[0]}.xlsx`)
  } catch (e) {
    console.error('Erro ao exportar Excel:', e)
    alert('Erro ao exportar Excel. Tente novamente.')
  }
}
</script>
