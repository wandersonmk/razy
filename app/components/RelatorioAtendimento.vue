<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Chart, registerables } from 'chart.js'
import { formatarDuracaoSegundos, formatarTelefone, useRelatorioAtendimento } from '~/composables/useRelatorioAtendimento'
Chart.register(...registerables)

const {
  metricas, diario, detalhes,
  isLoading, isLoadingDiario, isLoadingDetalhes,
  fetchMetricas, fetchDiario, fetchDetalhes
} = useRelatorioAtendimento()
const dias = ref(30)

const mensagensDiaRef = ref<HTMLCanvasElement | null>(null)
const tmprDiaRef = ref<HTMLCanvasElement | null>(null)
const mensagensProfRef = ref<HTMLCanvasElement | null>(null)
const atendimentosProfRef = ref<HTMLCanvasElement | null>(null)
const tmprProfRef = ref<HTMLCanvasElement | null>(null)
let mensagensDiaChart: Chart | null = null
let tmprDiaChart: Chart | null = null
let mensagensProfChart: Chart | null = null
let atendimentosProfChart: Chart | null = null
let tmprProfChart: Chart | null = null

const TOOLTIP_STYLE = {
  backgroundColor: '#1F2937',
  titleColor: '#F3F4F6',
  bodyColor: '#D1D5DB',
  borderColor: '#374151',
  borderWidth: 1,
  padding: 10,
  usePointStyle: true
}
const TICK_STYLE = { color: '#9CA3AF', font: { size: 11 } }
const GRID_STYLE = { color: 'rgba(148, 163, 184, 0.12)' }
const LEGEND_STYLE = { align: 'end' as const, labels: { color: '#9CA3AF', font: { size: 11 }, usePointStyle: true, pointStyle: 'circle' as const, boxWidth: 8, padding: 16 } }

let toast: any
onMounted(async () => { toast = await useToastSafe() })

async function carregar() {
  detalhesVisiveis.value = 15
  await Promise.all([fetchMetricas(dias.value), fetchDiario(dias.value), fetchDetalhes(dias.value)])
  await nextTick()
  desenharGraficos()
  setupObserverDetalhes()
}

onMounted(carregar)
watch(dias, carregar)
onBeforeUnmount(() => {
  mensagensDiaChart?.destroy()
  tmprDiaChart?.destroy()
  mensagensProfChart?.destroy()
  atendimentosProfChart?.destroy()
  tmprProfChart?.destroy()
  observerDetalhes?.disconnect()
})

// "Atendimentos por cliente" pode crescer muito (1 linha por conversa) — em
// vez de renderizar tudo de uma vez, mostra aos poucos conforme rola dentro
// da área com altura fixa (ver template). O PDF/Excel sempre exportam a
// lista INTEIRA (`detalhes.value`), independente do que está visível aqui.
const detalhesVisiveis = ref(15)
const sentinelDetalhes = ref<HTMLElement | null>(null)
let observerDetalhes: IntersectionObserver | null = null

function setupObserverDetalhes() {
  observerDetalhes?.disconnect()
  observerDetalhes = null
  nextTick(() => {
    if (!sentinelDetalhes.value || detalhes.value.length <= detalhesVisiveis.value) return
    observerDetalhes = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting && detalhesVisiveis.value < detalhes.value.length) {
        detalhesVisiveis.value += 15
      }
    })
    observerDetalhes.observe(sentinelDetalhes.value)
  })
}

// "Tempo de atendimento" (aberto → fechado) não existe aqui de propósito: depende
// de alguém clicar em "Fechar" no painel, o que não tem garantia de acontecer já
// que o profissional atende pelo próprio celular, sem usar o app. As 4 métricas
// abaixo são as que dá pra confiar 100%, porque nascem sozinhas no webhook:
// mensagens recebidas/enviadas, tempo até 1ª resposta e "atendimentos" (contado
// pela 1ª resposta automática — abertura, não fechamento).
const totais = computed(() => ({
  recebidas: metricas.value.reduce((s, m) => s + (m.mensagens_recebidas || 0), 0),
  enviadas: metricas.value.reduce((s, m) => s + (m.mensagens_enviadas || 0), 0),
  tmpr: mediaPonderada(metricas.value.map((m) => [m.tmpr_seg, m.mensagens_recebidas])),
  atendimentos: metricas.value.reduce((s, m) => s + (m.atendimentos || 0), 0)
}))

function mediaPonderada(pares: [number | null, number][]): number | null {
  let somaPeso = 0
  let somaValor = 0
  for (const [valor, peso] of pares) {
    if (valor === null || !peso) continue
    somaValor += valor * peso
    somaPeso += peso
  }
  return somaPeso > 0 ? somaValor / somaPeso : null
}

const labelsDia = computed(() =>
  diario.value.map((d) => new Date(d.dia + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }))
)
const temMensagensDia = computed(() => diario.value.some((d) => d.mensagens_recebidas > 0 || d.mensagens_enviadas > 0))
const temTmprDia = computed(() => diario.value.some((d) => d.tmpr_medio_seg !== null))
const temMensagensProf = computed(() => metricas.value.some((m) => m.mensagens_recebidas > 0 || m.mensagens_enviadas > 0))
const temAtendimentosProf = computed(() => metricas.value.some((m) => m.atendimentos > 0))
const temTmprProf = computed(() => metricas.value.some((m) => m.tmpr_seg !== null))

function desenharGraficos() {
  desenharMensagensDia()
  desenharTmprDia()
  desenharMensagensProf()
  desenharAtendimentosProf()
  desenharTmprProf()
}

function desenharMensagensDia() {
  mensagensDiaChart?.destroy()
  if (!mensagensDiaRef.value || !temMensagensDia.value) return
  const ctx = mensagensDiaRef.value.getContext('2d')
  if (!ctx) return
  mensagensDiaChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labelsDia.value,
      datasets: [
        { label: 'Recebidas', data: diario.value.map((d) => d.mensagens_recebidas), backgroundColor: 'rgba(59, 130, 246, 0.7)', borderRadius: 4, maxBarThickness: 20 },
        { label: 'Enviadas', data: diario.value.map((d) => d.mensagens_enviadas), backgroundColor: 'rgba(16, 185, 129, 0.7)', borderRadius: 4, maxBarThickness: 20 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      plugins: { legend: LEGEND_STYLE, tooltip: TOOLTIP_STYLE },
      scales: {
        x: { ticks: TICK_STYLE, grid: { display: false }, border: { display: false } },
        y: { beginAtZero: true, ticks: { ...TICK_STYLE, precision: 0 }, grid: GRID_STYLE, border: { display: false } }
      }
    }
  })
}

function desenharTmprDia() {
  tmprDiaChart?.destroy()
  if (!tmprDiaRef.value || !temTmprDia.value) return
  const ctx = tmprDiaRef.value.getContext('2d')
  if (!ctx) return
  tmprDiaChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labelsDia.value,
      datasets: [{
        label: 'Tempo até 1ª resposta (min)',
        data: diario.value.map((d) => (d.tmpr_medio_seg !== null ? Math.round((d.tmpr_medio_seg / 60) * 10) / 10 : null)),
        borderColor: '#F59E0B', backgroundColor: 'rgba(245, 158, 11, 0.12)', borderWidth: 2, fill: true, tension: 0.4, spanGaps: true,
        pointBackgroundColor: '#F59E0B', pointBorderColor: '#fff', pointBorderWidth: 2, pointRadius: 3
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      plugins: { legend: LEGEND_STYLE, tooltip: { ...TOOLTIP_STYLE, callbacks: { label: (c: any) => `${c.formattedValue} min` } } },
      scales: {
        x: { ticks: TICK_STYLE, grid: { display: false }, border: { display: false } },
        y: { beginAtZero: true, ticks: { ...TICK_STYLE, precision: 0 }, grid: GRID_STYLE, border: { display: false } }
      }
    }
  })
}

function desenharMensagensProf() {
  mensagensProfChart?.destroy()
  if (!mensagensProfRef.value || !temMensagensProf.value) return
  const ctx = mensagensProfRef.value.getContext('2d')
  if (!ctx) return
  const ordenado = [...metricas.value].sort((a, b) => b.mensagens_recebidas - a.mensagens_recebidas)
  mensagensProfChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ordenado.map((m) => m.profissional_nome),
      datasets: [
        { label: 'Recebidas', data: ordenado.map((m) => m.mensagens_recebidas), backgroundColor: 'rgba(59, 130, 246, 0.7)', borderRadius: 4, maxBarThickness: 16 },
        { label: 'Enviadas', data: ordenado.map((m) => m.mensagens_enviadas), backgroundColor: 'rgba(16, 185, 129, 0.7)', borderRadius: 4, maxBarThickness: 16 }
      ]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: LEGEND_STYLE, tooltip: TOOLTIP_STYLE },
      scales: {
        x: { beginAtZero: true, ticks: { ...TICK_STYLE, precision: 0 }, grid: GRID_STYLE, border: { display: false } },
        y: { ticks: TICK_STYLE, grid: { display: false }, border: { display: false } }
      }
    }
  })
}

function desenharAtendimentosProf() {
  atendimentosProfChart?.destroy()
  if (!atendimentosProfRef.value || !temAtendimentosProf.value) return
  const ctx = atendimentosProfRef.value.getContext('2d')
  if (!ctx) return
  const ordenado = [...metricas.value].sort((a, b) => b.atendimentos - a.atendimentos)
  atendimentosProfChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ordenado.map((m) => m.profissional_nome),
      datasets: [{ label: 'Atendimentos', data: ordenado.map((m) => m.atendimentos), backgroundColor: 'rgba(139, 92, 246, 0.75)', borderRadius: 4, maxBarThickness: 22 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: TOOLTIP_STYLE },
      scales: {
        x: { beginAtZero: true, ticks: { ...TICK_STYLE, precision: 0 }, grid: GRID_STYLE, border: { display: false } },
        y: { ticks: TICK_STYLE, grid: { display: false }, border: { display: false } }
      }
    }
  })
}

function desenharTmprProf() {
  tmprProfChart?.destroy()
  if (!tmprProfRef.value || !temTmprProf.value) return
  const ctx = tmprProfRef.value.getContext('2d')
  if (!ctx) return
  const ordenado = [...metricas.value].filter((m) => m.tmpr_seg !== null).sort((a, b) => (a.tmpr_seg || 0) - (b.tmpr_seg || 0))
  tmprProfChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ordenado.map((m) => m.profissional_nome),
      datasets: [{ label: 'Tempo até 1ª resposta (min)', data: ordenado.map((m) => Math.round(((m.tmpr_seg || 0) / 60) * 10) / 10), backgroundColor: 'rgba(245, 158, 11, 0.75)', borderRadius: 4, maxBarThickness: 22 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { ...TOOLTIP_STYLE, callbacks: { label: (c: any) => `${c.formattedValue} min` } } },
      scales: {
        x: { beginAtZero: true, ticks: { ...TICK_STYLE, precision: 0 }, grid: GRID_STYLE, border: { display: false } },
        y: { ticks: TICK_STYLE, grid: { display: false }, border: { display: false } }
      }
    }
  })
}

// ── Exportar ──────────────────────────────────────────────────────────────────
function periodoLabel(): string {
  return dias.value === 7 ? 'Últimos 7 dias' : dias.value === 90 ? 'Últimos 90 dias' : 'Últimos 30 dias'
}

function pdfSafe(s: string | null | undefined): string {
  return (s || '')
    .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE00}-\u{FE0F}\u{2190}-\u{21FF}\u{2300}-\u{23FF}]/gu, '')
    .replace(/[^\x00-\xFF]/g, '')
    .trim()
}

function formatarDataHora(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const podeExportar = computed(() => metricas.value.length > 0 || detalhes.value.length > 0)

async function exportarPDF() {
  if (typeof window === 'undefined') return
  if (!podeExportar.value) { toast?.warning('Sem dados no período selecionado pra exportar'); return }
  try {
    const { jsPDF } = await import('jspdf')
    const autoTable = (await import('jspdf-autotable')).default
    const doc = new jsPDF({ orientation: 'landscape' })
    const agora = new Date()
    const ROXO: [number, number, number] = [102, 90, 228]

    // Cabeçalho de marca
    doc.setFillColor(...ROXO)
    doc.rect(0, 0, 297, 32, 'F')
    doc.setTextColor(255, 255, 255)
    doc.setFontSize(20)
    doc.setFont('helvetica', 'bold')
    doc.text('Razy', 14, 15)
    doc.setFontSize(11)
    doc.setFont('helvetica', 'normal')
    doc.text('Relatório de Atendimento — canal por profissional', 14, 24)

    doc.setTextColor(90, 90, 90)
    doc.setFontSize(9)
    doc.text(`Gerado em ${agora.toLocaleString('pt-BR')}  ·  Período: ${periodoLabel()}`, 14, 40)

    // Cards de resumo (mesmos totais do topo da tela)
    const cards: { rotulo: string; valor: string }[] = [
      { rotulo: 'Mensagens recebidas', valor: totais.value.recebidas.toLocaleString('pt-BR') },
      { rotulo: 'Mensagens enviadas', valor: totais.value.enviadas.toLocaleString('pt-BR') },
      { rotulo: 'Tempo até 1ª resposta', valor: pdfSafe(formatarDuracaoSegundos(totais.value.tmpr)) },
      { rotulo: 'Atendimentos no período', valor: totais.value.atendimentos.toLocaleString('pt-BR') }
    ]
    const cardW = 66
    cards.forEach((c, i) => {
      const x = 14 + i * (cardW + 4)
      doc.setDrawColor(225, 225, 230)
      doc.setFillColor(250, 250, 252)
      doc.roundedRect(x, 46, cardW, 20, 2, 2, 'FD')
      doc.setTextColor(40, 40, 40)
      doc.setFontSize(13)
      doc.setFont('helvetica', 'bold')
      doc.text(c.valor, x + 5, 57)
      doc.setTextColor(120, 120, 120)
      doc.setFontSize(7.5)
      doc.setFont('helvetica', 'normal')
      doc.text(pdfSafe(c.rotulo), x + 5, 63)
    })

    let y = 76
    doc.setTextColor(30, 30, 30)
    doc.setFontSize(12)
    doc.setFont('helvetica', 'bold')
    doc.text('Resumo por profissional', 14, y)

    autoTable(doc, {
      startY: y + 4,
      head: [['Profissional', 'Recebidas', 'Enviadas', 'Atendimentos', 'Tempo até 1ª resposta']],
      body: metricas.value.map((m) => [
        pdfSafe(m.profissional_nome) || '—',
        m.mensagens_recebidas,
        m.mensagens_enviadas,
        m.atendimentos,
        pdfSafe(formatarDuracaoSegundos(m.tmpr_seg))
      ]),
      theme: 'striped',
      styles: { fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: ROXO, textColor: 255, fontStyle: 'bold' },
      alternateRowStyles: { fillColor: [249, 250, 251] },
      margin: { left: 14, right: 14 }
    })

    // Detalhe por cliente — sempre em página nova, é a seção que o dono da
    // empresa mais quer ver (quem cada profissional atendeu de verdade).
    doc.addPage()
    doc.setTextColor(30, 30, 30)
    doc.setFontSize(12)
    doc.setFont('helvetica', 'bold')
    doc.text('Atendimentos por cliente', 14, 18)
    doc.setTextColor(120, 120, 120)
    doc.setFontSize(8.5)
    doc.setFont('helvetica', 'normal')
    doc.text('Cada linha é 1 conversa — telefone e nome do cliente, quem atendeu e o tempo até a 1ª resposta.', 14, 24)

    autoTable(doc, {
      startY: 30,
      head: [['Profissional', 'Cliente', 'Telefone', '1ª mensagem', 'Receb.', 'Env.', 'Tempo até 1ª resposta']],
      body: detalhes.value.map((d) => [
        pdfSafe(d.profissional_nome) || '—',
        pdfSafe(d.cliente_nome) || '—',
        formatarTelefone(d.cliente_numero),
        formatarDataHora(d.primeira_recebida_em),
        d.mensagens_recebidas,
        d.mensagens_enviadas,
        pdfSafe(formatarDuracaoSegundos(d.tmpr_seg))
      ]),
      theme: 'striped',
      styles: { fontSize: 8.5, cellPadding: 2.5 },
      headStyles: { fillColor: ROXO, textColor: 255, fontStyle: 'bold' },
      alternateRowStyles: { fillColor: [249, 250, 251] },
      margin: { left: 14, right: 14 },
      didDrawPage: () => {
        doc.setFontSize(8)
        doc.setTextColor(150, 150, 150)
        doc.text(`Razy · gerado em ${agora.toLocaleDateString('pt-BR')}`, 14, doc.internal.pageSize.getHeight() - 8)
      }
    })

    doc.save(`relatorio-atendimento-${agora.toISOString().split('T')[0]}.pdf`)
    toast?.success('PDF exportado')
  } catch (e: any) {
    console.error('Erro ao exportar PDF:', e)
    toast?.error(e?.message || 'Erro ao exportar PDF. Tente novamente.')
  }
}

async function exportarExcel() {
  if (typeof window === 'undefined') return
  if (!podeExportar.value) { toast?.warning('Sem dados no período selecionado pra exportar'); return }
  try {
    const XLSX = await import('xlsx')
    const agora = new Date()

    const resumo: any[][] = [
      ['Razy - Relatório de Atendimento por Profissional'],
      [`Gerado em: ${agora.toLocaleString('pt-BR')}`],
      [`Período: ${periodoLabel()}`],
      [],
      ['#', 'Profissional', 'Mensagens recebidas', 'Mensagens enviadas', 'Atendimentos', 'Tempo até 1ª resposta (seg)', 'Tempo até 1ª resposta']
    ]
    metricas.value.forEach((m, i) => {
      resumo.push([
        (i + 1).toString(),
        m.profissional_nome,
        m.mensagens_recebidas,
        m.mensagens_enviadas,
        m.atendimentos,
        m.tmpr_seg !== null ? Math.round(m.tmpr_seg) : '',
        formatarDuracaoSegundos(m.tmpr_seg)
      ])
    })

    const porCliente: any[][] = [
      ['Razy - Atendimentos por cliente'],
      [`Gerado em: ${agora.toLocaleString('pt-BR')}`],
      [`Período: ${periodoLabel()}`],
      [],
      ['#', 'Profissional', 'Cliente', 'Telefone', 'Primeira mensagem em', 'Mensagens recebidas', 'Mensagens enviadas', 'Tempo até 1ª resposta (seg)', 'Tempo até 1ª resposta']
    ]
    detalhes.value.forEach((d, i) => {
      porCliente.push([
        (i + 1).toString(),
        d.profissional_nome || '—',
        d.cliente_nome || '—',
        formatarTelefone(d.cliente_numero),
        formatarDataHora(d.primeira_recebida_em),
        d.mensagens_recebidas,
        d.mensagens_enviadas,
        d.tmpr_seg !== null ? Math.round(d.tmpr_seg) : '',
        formatarDuracaoSegundos(d.tmpr_seg)
      ])
    })

    const wb = XLSX.utils.book_new()

    const wsResumo = XLSX.utils.aoa_to_sheet(resumo)
    wsResumo['!cols'] = [{ wch: 5 }, { wch: 26 }, { wch: 20 }, { wch: 20 }, { wch: 14 }, { wch: 24 }, { wch: 22 }]
    XLSX.utils.book_append_sheet(wb, wsResumo, 'Resumo por profissional')

    const wsCliente = XLSX.utils.aoa_to_sheet(porCliente)
    wsCliente['!cols'] = [{ wch: 5 }, { wch: 22 }, { wch: 24 }, { wch: 18 }, { wch: 20 }, { wch: 18 }, { wch: 18 }, { wch: 24 }, { wch: 20 }]
    XLSX.utils.book_append_sheet(wb, wsCliente, 'Atendimentos por cliente')

    XLSX.writeFile(wb, `relatorio-atendimento-${agora.toISOString().split('T')[0]}.xlsx`)
    toast?.success('Excel exportado')
  } catch (e: any) {
    console.error('Erro ao exportar Excel:', e)
    toast?.error(e?.message || 'Erro ao exportar Excel. Tente novamente.')
  }
}
</script>

<template>
  <div>
    <!-- Título/descrição ficam no cabeçalho da página (dashboard.vue), sincronizado
         com a aba ativa — aqui só os controles (período + exportar). -->
    <div class="flex items-center justify-end gap-3 flex-wrap p-6 border-b border-border">
      <div class="flex items-center gap-2">
        <select
          v-model.number="dias"
          class="px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        >
          <option :value="7">Últimos 7 dias</option>
          <option :value="30">Últimos 30 dias</option>
          <option :value="90">Últimos 90 dias</option>
        </select>
        <button
          @click="exportarPDF"
          :disabled="!podeExportar"
          class="flex items-center justify-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg transition-colors text-sm font-medium"
          title="Exportar para PDF"
        >
          <Icon icon="file-pdf" class-name="w-4 h-4" fallback="" />
          <span class="hidden sm:inline">PDF</span>
        </button>
        <button
          @click="exportarExcel"
          :disabled="!podeExportar"
          class="flex items-center justify-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg transition-colors text-sm font-medium"
          title="Exportar para Excel"
        >
          <Icon icon="file-excel" class-name="w-4 h-4" fallback="" />
          <span class="hidden sm:inline">Excel</span>
        </button>
      </div>
    </div>

    <!-- Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 p-6 border-b border-border">
      <div class="rounded-xl border border-blue-800/20 bg-blue-950/5 p-4">
        <p class="text-2xl font-bold tabular-nums text-blue-500">{{ totais.recebidas.toLocaleString('pt-BR') }}</p>
        <p class="text-xs text-muted-foreground mt-1">Mensagens recebidas</p>
      </div>
      <div class="rounded-xl border border-green-800/20 bg-green-950/5 p-4">
        <p class="text-2xl font-bold tabular-nums text-green-500">{{ totais.enviadas.toLocaleString('pt-BR') }}</p>
        <p class="text-xs text-muted-foreground mt-1">Mensagens enviadas</p>
      </div>
      <div class="rounded-xl border border-amber-800/20 bg-amber-950/5 p-4">
        <p class="text-2xl font-bold tabular-nums text-amber-500">{{ formatarDuracaoSegundos(totais.tmpr) }}</p>
        <p class="text-xs text-muted-foreground mt-1">Tempo até 1ª resposta</p>
      </div>
      <div class="rounded-xl border border-violet-800/20 bg-violet-950/5 p-4">
        <p class="text-2xl font-bold tabular-nums text-violet-500">{{ totais.atendimentos.toLocaleString('pt-BR') }}</p>
        <p class="text-xs text-muted-foreground mt-1">Atendimentos no período</p>
      </div>
    </div>

    <!-- Gráficos diários -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 border-b border-border">
      <div class="flex flex-col rounded-xl border border-border bg-card p-5">
        <h4 class="mb-3 text-sm font-semibold text-foreground">Mensagens por dia</h4>
        <div class="relative min-h-[14rem] flex-1">
          <div v-if="isLoadingDiario" class="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">Carregando...</div>
          <canvas v-else-if="temMensagensDia" ref="mensagensDiaRef" />
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center">
            <svg class="h-8 w-8 text-muted-foreground/40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 3v18h18M7 14l4-4 3 3 5-6"/></svg>
            <p class="text-sm text-muted-foreground">Sem mensagens no período</p>
          </div>
        </div>
      </div>

      <div class="flex flex-col rounded-xl border border-border bg-card p-5">
        <h4 class="mb-3 text-sm font-semibold text-foreground">Tempo até a 1ª resposta</h4>
        <p class="text-xs text-muted-foreground -mt-2 mb-3">Tempo entre a 1ª mensagem do cliente e a 1ª resposta do profissional/IA, por dia.</p>
        <div class="relative min-h-[14rem] flex-1">
          <div v-if="isLoadingDiario" class="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">Carregando...</div>
          <canvas v-else-if="temTmprDia" ref="tmprDiaRef" />
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center">
            <svg class="h-8 w-8 text-muted-foreground/40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <p class="text-sm text-muted-foreground">Sem 1ª resposta registrada no período</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Comparação por profissional -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 border-b border-border">
      <div class="flex flex-col rounded-xl border border-border bg-card p-5">
        <h4 class="mb-3 text-sm font-semibold text-foreground">Mensagens por profissional</h4>
        <div class="relative" :style="{ minHeight: Math.max(140, metricas.length * 34) + 'px' }">
          <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">Carregando...</div>
          <canvas v-else-if="temMensagensProf" ref="mensagensProfRef" />
          <div v-else class="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">Sem dados no período</div>
        </div>
      </div>

      <div class="flex flex-col rounded-xl border border-border bg-card p-5">
        <h4 class="mb-3 text-sm font-semibold text-foreground">Atendimentos por profissional</h4>
        <div class="relative" :style="{ minHeight: Math.max(140, metricas.length * 34) + 'px' }">
          <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">Carregando...</div>
          <canvas v-else-if="temAtendimentosProf" ref="atendimentosProfRef" />
          <div v-else class="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">Sem dados no período</div>
        </div>
      </div>
    </div>

    <div class="p-6 border-b border-border">
      <div class="flex flex-col rounded-xl border border-border bg-card p-5">
        <h4 class="mb-3 text-sm font-semibold text-foreground">Tempo até 1ª resposta por profissional</h4>
        <div class="relative" :style="{ minHeight: Math.max(140, metricas.length * 34) + 'px' }">
          <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">Carregando...</div>
          <canvas v-else-if="temTmprProf" ref="tmprProfRef" />
          <div v-else class="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">Sem 1ª resposta registrada no período</div>
        </div>
      </div>
    </div>

    <!-- Tabela detalhada -->
    <div class="p-6">
      <div v-if="isLoading" class="text-center py-10 text-muted-foreground text-sm">Carregando métricas...</div>

      <div v-else-if="!metricas.length" class="text-center py-10">
        <p class="text-foreground font-medium">Nenhum dado ainda</p>
        <p class="text-sm text-muted-foreground mt-1">
          Assim que profissionais cadastrados em
          <NuxtLink to="/profissionais" class="text-primary hover:underline">Profissionais &amp; Canais</NuxtLink>
          trocarem mensagens, as métricas aparecem aqui.
        </p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-muted border-b border-border">
            <tr>
              <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Profissional</th>
              <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Mensagens recebidas</th>
              <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Mensagens enviadas</th>
              <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Atendimentos</th>
              <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Tempo até 1ª resposta</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in metricas" :key="m.profissional_id" class="border-b border-border/50 hover:bg-muted/30 transition-colors">
              <td class="py-3 px-3 font-medium text-foreground whitespace-nowrap">{{ m.profissional_nome }}</td>
              <td class="py-3 px-3 tabular-nums text-foreground">{{ m.mensagens_recebidas.toLocaleString('pt-BR') }}</td>
              <td class="py-3 px-3 tabular-nums text-foreground">{{ m.mensagens_enviadas.toLocaleString('pt-BR') }}</td>
              <td class="py-3 px-3 tabular-nums text-foreground">{{ m.atendimentos.toLocaleString('pt-BR') }}</td>
              <td class="py-3 px-3 tabular-nums text-foreground">{{ formatarDuracaoSegundos(m.tmpr_seg) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Detalhe por cliente — quem cada profissional atendeu de verdade -->
    <div class="p-6 border-t border-border">
      <h4 class="text-sm font-semibold text-foreground">Atendimentos por cliente</h4>
      <p class="text-xs text-muted-foreground mt-0.5 mb-4">Cada linha é 1 conversa — telefone e nome do cliente, quem atendeu e o tempo até a 1ª resposta.</p>

      <div v-if="isLoadingDetalhes" class="text-center py-10 text-muted-foreground text-sm">Carregando atendimentos...</div>

      <div v-else-if="!detalhes.length" class="text-center py-10">
        <p class="text-sm text-muted-foreground">Nenhum atendimento no período.</p>
      </div>

      <div v-else class="overflow-x-auto">
        <div style="max-height: 480px; overflow-y: auto;">
          <table class="w-full text-sm">
            <thead class="bg-muted sticky top-0 z-10 border-b border-border">
              <tr>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Profissional</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Cliente</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Telefone</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">1ª mensagem</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Recebidas</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Enviadas</th>
                <th class="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs">Tempo até 1ª resposta</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in detalhes.slice(0, detalhesVisiveis)" :key="d.conversa_id" class="border-b border-border/50 hover:bg-muted/30 transition-colors">
                <td class="py-3 px-3 font-medium text-foreground whitespace-nowrap">{{ d.profissional_nome || '—' }}</td>
                <td class="py-3 px-3 text-foreground whitespace-nowrap">{{ d.cliente_nome || '—' }}</td>
                <td class="py-3 px-3 tabular-nums text-foreground whitespace-nowrap">{{ formatarTelefone(d.cliente_numero) }}</td>
                <td class="py-3 px-3 text-muted-foreground whitespace-nowrap">{{ formatarDataHora(d.primeira_recebida_em) }}</td>
                <td class="py-3 px-3 tabular-nums text-foreground">{{ d.mensagens_recebidas.toLocaleString('pt-BR') }}</td>
                <td class="py-3 px-3 tabular-nums text-foreground">{{ d.mensagens_enviadas.toLocaleString('pt-BR') }}</td>
                <td class="py-3 px-3 tabular-nums text-foreground">{{ formatarDuracaoSegundos(d.tmpr_seg) }}</td>
              </tr>
              <tr v-if="detalhesVisiveis < detalhes.length">
                <td :colspan="7"><div ref="sentinelDetalhes" style="height: 1px;" /></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="detalhesVisiveis < detalhes.length" class="text-xs text-muted-foreground text-center py-2">
          Mostrando {{ detalhesVisiveis }} de {{ detalhes.length }} — role pra carregar mais
        </p>
      </div>
    </div>
  </div>
</template>
