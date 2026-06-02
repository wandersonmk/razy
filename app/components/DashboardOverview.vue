<template>
  <div class="w-full space-y-6">
    <!-- Cards de métricas -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

      <!-- Total Disparados -->
      <div class="relative bg-gradient-to-br from-card via-green-950/10 to-card text-card-foreground rounded-xl border border-green-800/20 shadow-sm hover:shadow-md hover:shadow-green-500/10 transition-all duration-300 p-6 group overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-green-500/8 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"/>
        <div class="relative z-10 flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground mb-1">Total Enviados</p>
            <p class="text-2xl font-bold text-foreground">{{ metrics.totalEnviados.toLocaleString('pt-BR') }}</p>
            <p class="text-xs text-green-500 mt-1">mensagens disparadas</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center shadow-lg shrink-0">
            <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654z"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Total Falhas -->
      <div class="relative bg-gradient-to-br from-card via-red-950/10 to-card text-card-foreground rounded-xl border border-red-800/20 shadow-sm hover:shadow-md hover:shadow-red-500/10 transition-all duration-300 p-6 group overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-red-500/8 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"/>
        <div class="relative z-10 flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground mb-1">Total Falhas</p>
            <p class="text-2xl font-bold text-foreground">{{ metrics.totalFalhas.toLocaleString('pt-BR') }}</p>
            <p class="text-xs text-red-500 mt-1">envios com erro</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center shadow-lg shrink-0">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Campanhas -->
      <div class="relative bg-gradient-to-br from-card via-primary/5 to-card text-card-foreground rounded-xl border border-primary/20 shadow-sm hover:shadow-md hover:shadow-primary/10 transition-all duration-300 p-6 group overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-primary/8 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"/>
        <div class="relative z-10 flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground mb-1">Campanhas</p>
            <p class="text-2xl font-bold text-foreground">{{ metrics.totalCampanhas }}</p>
            <p class="text-xs text-primary mt-1">total criadas</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-primary to-blue-700 rounded-lg flex items-center justify-center shadow-lg shrink-0">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Total Contatos -->
      <div class="relative bg-gradient-to-br from-card via-indigo-950/10 to-card text-card-foreground rounded-xl border border-indigo-800/20 shadow-sm hover:shadow-md hover:shadow-indigo-500/10 transition-all duration-300 p-6 group overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-indigo-500/8 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"/>
        <div class="relative z-10 flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground mb-1">Total Contatos</p>
            <p class="text-2xl font-bold text-foreground">{{ metrics.totalContatos.toLocaleString('pt-BR') }}</p>
            <p class="text-xs text-indigo-400 mt-1">em todos os públicos</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg shrink-0">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Segunda linha: Taxa de entrega + Gráfico -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">

      <!-- Taxa de entrega -->
      <div class="flex h-full flex-col rounded-xl border border-border bg-card p-6">
        <h3 class="text-sm font-semibold text-foreground">Taxa de Entrega</h3>

        <div class="flex flex-1 items-center justify-center py-6">
          <CircularProgress
            :total="metrics.totalEnviados + metrics.totalFalhas"
            :value="metrics.totalEnviados"
          />
        </div>

        <div class="grid grid-cols-3 gap-2 border-t border-border pt-4">
          <div class="flex flex-col items-center gap-1">
            <span class="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span class="h-2 w-2 rounded-full bg-green-500"/> Enviados
            </span>
            <span class="text-lg font-bold tabular-nums text-green-500">{{ metrics.totalEnviados.toLocaleString('pt-BR') }}</span>
          </div>
          <div class="flex flex-col items-center gap-1">
            <span class="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span class="h-2 w-2 rounded-full bg-red-500"/> Falhas
            </span>
            <span class="text-lg font-bold tabular-nums text-red-500">{{ metrics.totalFalhas.toLocaleString('pt-BR') }}</span>
          </div>
          <div class="flex flex-col items-center gap-1">
            <span class="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span class="h-2 w-2 rounded-full bg-primary"/> Respostas
            </span>
            <span class="text-lg font-bold tabular-nums text-primary">{{ metrics.totalRespostas.toLocaleString('pt-BR') }}</span>
          </div>
        </div>
      </div>

      <!-- Gráfico de disparos por mês -->
      <div class="flex h-full flex-col rounded-xl border border-border bg-card p-6 lg:col-span-2">
        <h3 class="mb-4 text-sm font-semibold text-foreground">Disparos nos Últimos 6 Meses</h3>
        <div class="relative min-h-[16rem] flex-1">
          <canvas v-show="chartHasData" ref="lineChartRef"/>
          <!-- Empty state (skill §10 empty-data-state) -->
          <div
            v-if="!chartHasData"
            class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2 text-center"
          >
            <svg class="h-10 w-10 text-muted-foreground/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 3v18h18M7 14l4-4 3 3 5-6"/>
            </svg>
            <p class="text-sm font-medium text-muted-foreground">Nenhum disparo nos últimos 6 meses</p>
            <p class="text-xs text-muted-foreground/70">Os dados aparecerão aqui após sua primeira campanha</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Campanhas recentes -->
    <div class="bg-card border border-border rounded-xl p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-foreground">Campanhas Recentes</h3>
        <NuxtLink to="/campanhas" class="text-xs text-primary hover:underline">Ver todas</NuxtLink>
      </div>
      <div v-if="campanhasRecentes.length === 0" class="text-center py-6 text-muted-foreground text-sm">
        Nenhuma campanha ainda.
        <NuxtLink to="/campanhas" class="text-primary hover:underline ml-1">Criar campanha →</NuxtLink>
      </div>
      <div v-else class="space-y-2">
        <div v-for="c in campanhasRecentes" :key="c.id" class="flex items-center justify-between py-2 border-b border-border last:border-0">
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-foreground truncate">{{ c.nome }}</p>
            <p class="text-xs text-muted-foreground">{{ new Date(c.created_at).toLocaleDateString('pt-BR') }}</p>
          </div>
          <div class="flex items-center gap-4 text-xs shrink-0">
            <span class="text-green-500 font-medium">{{ c.total_enviados }} enviados</span>
            <span v-if="c.total_falhas > 0" class="text-red-500">{{ c.total_falhas }} falhas</span>
            <span v-if="c.total_respostas > 0" class="text-primary font-medium">{{ c.total_respostas }} responderam</span>
            <span :class="statusCores[c.status]" class="px-2 py-0.5 rounded-full">{{ statusLabels[c.status] }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

const lineChartRef = ref<HTMLCanvasElement | null>(null)
const chartHasData = ref(false)

const metrics = ref({
  totalEnviados: 0,
  totalFalhas: 0,
  totalRespostas: 0,
  totalCampanhas: 0,
  totalContatos: 0
})

const campanhasRecentes = ref<any[]>([])

const statusLabels: Record<string, string> = {
  rascunho: 'Rascunho', em_andamento: 'Em andamento',
  concluida: 'Concluída', pausada: 'Pausada', falhou: 'Falhou'
}
const statusCores: Record<string, string> = {
  rascunho: 'bg-muted text-muted-foreground',
  em_andamento: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  concluida: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  pausada: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  falhou: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
}

async function fetchMetricas() {
  if (!process.client) return
  const supabase = useSupabaseClient()

  const [campanhasRes, contatosRes, recentesRes] = await Promise.all([
    supabase.from('campanhas').select('id, total_enviados, total_falhas, status'),
    supabase.from('contatos').select('id', { count: 'exact', head: true }),
    supabase.from('campanhas').select('id, nome, status, total_enviados, total_falhas, created_at').eq('arquivada', false).order('created_at', { ascending: false }).limit(5)
  ])

  // Respostas reais = contatos distintos que responderam (1 por cliente), derivadas
  // dos disparos — não do contador total_respostas (que pode dessincronizar).
  const mapaRespostas = await contarRespostasPorCampanha(
    supabase,
    (campanhasRes.data || []).map((c: any) => c.id)
  )

  if (campanhasRes.data) {
    metrics.value.totalEnviados = campanhasRes.data.reduce((s: number, c: any) => s + (c.total_enviados || 0), 0)
    metrics.value.totalFalhas = campanhasRes.data.reduce((s: number, c: any) => s + (c.total_falhas || 0), 0)
    metrics.value.totalRespostas = campanhasRes.data.reduce((s: number, c: any) => s + (mapaRespostas.get(c.id) || 0), 0)
    metrics.value.totalCampanhas = campanhasRes.data.length
  }

  if (!campanhasRes.error && typeof contatosRes.count === 'number') {
    metrics.value.totalContatos = contatosRes.count
  }

  campanhasRecentes.value = (recentesRes.data || []).map((c: any) => ({
    ...c,
    total_respostas: mapaRespostas.get(c.id) ?? 0
  }))
}

async function createLineChart() {
  if (!lineChartRef.value) return
  const supabase = useSupabaseClient()
  const now = new Date()
  const labels: string[] = []
  const dataEnviados: number[] = []
  const dataFalhas: number[] = []

  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const label = d.toLocaleString('pt-BR', { month: 'short' })
    labels.push(label.charAt(0).toUpperCase() + label.slice(1))

    const firstDay = new Date(d.getFullYear(), d.getMonth(), 1)
    const lastDay = new Date(d.getFullYear(), d.getMonth() + 1, 0)
    firstDay.setHours(0, 0, 0, 0)
    lastDay.setHours(23, 59, 59, 999)

    const { data } = await supabase
      .from('disparos')
      .select('status')
      .gte('created_at', firstDay.toISOString())
      .lte('created_at', lastDay.toISOString())

    const enviados = data?.filter((d: any) => d.status === 'enviado').length || 0
    const falhas = data?.filter((d: any) => d.status === 'falhou').length || 0
    dataEnviados.push(enviados)
    dataFalhas.push(falhas)
  }

  // Só renderiza o gráfico quando há dados; caso contrário mostra o empty state
  const total = dataEnviados.reduce((s, n) => s + n, 0) + dataFalhas.reduce((s, n) => s + n, 0)
  chartHasData.value = total > 0
  if (!chartHasData.value) return

  await nextTick()
  const canvas = lineChartRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Enviados',
          data: dataEnviados,
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#10B981',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 4
        },
        {
          label: 'Falhas',
          data: dataFalhas,
          borderColor: '#EF4444',
          backgroundColor: 'rgba(239, 68, 68, 0.05)',
          borderWidth: 2,
          fill: false,
          tension: 0.4,
          pointBackgroundColor: '#EF4444',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          align: 'end',
          labels: { color: '#9CA3AF', font: { size: 11 }, usePointStyle: true, pointStyle: 'circle', boxWidth: 8, padding: 16 }
        },
        tooltip: {
          backgroundColor: '#1F2937',
          titleColor: '#F3F4F6',
          bodyColor: '#D1D5DB',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 10,
          usePointStyle: true
        }
      },
      scales: {
        x: {
          ticks: { color: '#9CA3AF', font: { size: 11 } },
          grid: { display: false },
          border: { display: false }
        },
        y: {
          beginAtZero: true,
          ticks: { color: '#9CA3AF', font: { size: 11 }, precision: 0 },
          grid: { color: 'rgba(148, 163, 184, 0.12)' },
          border: { display: false }
        }
      }
    }
  })
}

onMounted(() => {
  nextTick(async () => {
    await fetchMetricas()
    createLineChart()
  })
})
</script>
