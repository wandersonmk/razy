<script setup lang="ts">
/**
 * Gráfico de uma resposta do Analista.
 *
 * Os dados vêm prontos do backend, derivados do retorno real das consultas —
 * o modelo de linguagem não escolhe número nem rótulo aqui. Gráfico com valor
 * inventado é pior que gráfico nenhum: ele empresta credibilidade que o dado
 * não tem.
 *
 * Tema: os gráficos antigos do painel fixam cinza/grafite no código e só ficam
 * legíveis no escuro. Aqui as cores da moldura (eixo, grade, tooltip) saem dos
 * tokens do tema e o gráfico é redesenhado quando o usuário troca claro/escuro
 * — a classe `.light` no <html> é observada por MutationObserver.
 */
import { Chart, registerables } from 'chart.js'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { GraficoSpec } from '~/composables/useAnalista'

Chart.register(...registerables)

const props = defineProps<{ spec: GraficoSpec }>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null
let observer: MutationObserver | null = null

// Paleta das séries: escolhida para manter contraste nos DOIS fundos, então
// não muda com o tema (só a moldura muda).
const CORES: Record<string, string> = {
  azul: '#3B82F6',
  verde: '#10B981',
  ambar: '#F59E0B',
  rosa: '#F43F5E',
  violeta: '#8B5CF6'
}

function corDe(nome?: string): string {
  return CORES[nome || 'azul'] || CORES.azul!
}

const ehRosca = computed(() => props.spec?.tipo === 'rosca')

// Legenda da rosca em HTML, não desenhada no canvas: texto em <canvas> é pintado
// por opção do Chart.js e não responde a classe Tailwind nenhuma — qualquer
// desalinhamento entre essa opção e o tema vigente deixa a legenda ilegível
// num dos dois modos. Como HTML normal ela usa a mesma classe de cor que o
// resto do card já usa, e já provou responder ao tema corretamente.
const legendaRosca = computed(() => {
  if (!ehRosca.value) return []
  const spec = props.spec
  const serie = spec.series?.[0]
  if (!serie) return []
  const cores = (serie.cores?.length ? serie.cores : spec.labels.map((_, i) => ['azul', 'verde', 'violeta'][i])).map(corDe)
  const total = serie.dados.reduce((s, n) => s + (Number(n) || 0), 0)
  return spec.labels.map((rotulo, i) => {
    const v = Number(serie.dados[i]) || 0
    const pct = total ? Math.round((v / total) * 100) : 0
    return { rotulo, valor: v, pct, cor: cores[i] }
  })
})

/** Moldura (eixos, grade, tooltip) lida do tema atual. */
function moldura() {
  const claro = typeof document !== 'undefined' && document.documentElement.classList.contains('light')
  return {
    texto: claro ? '#6B7280' : '#A0A3AC',
    grade: claro ? 'rgba(17, 24, 39, 0.08)' : 'rgba(148, 163, 184, 0.12)',
    tooltipFundo: claro ? '#FFFFFF' : '#26272B',
    tooltipTitulo: claro ? '#111827' : '#FFFFFF',
    tooltipTexto: claro ? '#374151' : '#D1D5DB',
    tooltipBorda: claro ? '#E5E7EB' : '#35363B'
  }
}

function desenhar() {
  chart?.destroy()
  chart = null

  const el = canvasRef.value
  const spec = props.spec
  if (!el || !spec?.series?.length) return
  const ctx = el.getContext('2d')
  if (!ctx) return

  const m = moldura()
  const serie = spec.series[0]!
  const sufixo = spec.sufixo || ''
  const horizontal = spec.tipo === 'barras_h'
  const rosca = spec.tipo === 'rosca'

  // Valor desenhado na barra, não só no tooltip: num painel de leitura rápida,
  // ter de passar o mouse em cada barra para saber quanto vale anula o ganho
  // de ter um gráfico.
  const rotulosDeValor = {
    id: 'rotulosDeValor',
    afterDatasetsDraw(grafico: any) {
      const c = grafico.ctx
      c.save()
      c.font = '600 11px ui-sans-serif, system-ui, sans-serif'
      c.fillStyle = m.texto
      grafico.getDatasetMeta(0).data.forEach((el: any, i: number) => {
        const valor = serie.dados[i]
        if (valor == null) return
        const texto = `${valor}${sufixo}`
        if (horizontal) {
          c.textAlign = 'left'
          c.textBaseline = 'middle'
          c.fillText(texto, el.x + 6, el.y)
        } else {
          c.textAlign = 'center'
          c.textBaseline = 'bottom'
          c.fillText(texto, el.x, el.y - 5)
        }
      })
      c.restore()
    }
  }

  const tooltip = {
    backgroundColor: m.tooltipFundo,
    titleColor: m.tooltipTitulo,
    bodyColor: m.tooltipTexto,
    borderColor: m.tooltipBorda,
    borderWidth: 1,
    padding: 10,
    usePointStyle: true,
    callbacks: { label: (c: any) => ` ${c.formattedValue}${sufixo}` }
  }

  if (rosca) {
    const cores = (serie.cores || []).map(corDe)
    chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: spec.labels,
        datasets: [{
          data: serie.dados,
          backgroundColor: cores.length ? cores : spec.labels.map((_, i) => corDe(['azul', 'verde', 'violeta'][i])),
          borderWidth: 0,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        // Legenda vem como HTML ao lado do canvas (ver legendaRosca) — nada de
        // texto pintado aqui dentro.
        plugins: { legend: { display: false }, tooltip }
      }
    })
    return
  }

  chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: spec.labels,
      datasets: [{
        label: serie.nome,
        data: serie.dados,
        backgroundColor: corDe(serie.cor),
        borderRadius: 5,
        maxBarThickness: horizontal ? 16 : 34
      }]
    },
    options: {
      indexAxis: horizontal ? 'y' : 'x',
      responsive: true,
      maintainAspectRatio: false,
      // Espaço para o número ao lado (ou acima) da barra mais longa.
      layout: { padding: horizontal ? { right: 42 } : { top: 18 } },
      plugins: { legend: { display: false }, tooltip },
      scales: {
        x: {
          beginAtZero: horizontal,
          ticks: { color: m.texto, font: { size: 11 }, precision: 0 },
          grid: horizontal ? { color: m.grade } : { display: false },
          border: { display: false }
        },
        y: {
          beginAtZero: !horizontal,
          ticks: { color: m.texto, font: { size: 11 }, precision: 0 },
          grid: horizontal ? { display: false } : { color: m.grade },
          border: { display: false }
        }
      }
    },
    plugins: [rotulosDeValor]
  })
}

/** Imagem do gráfico para embutir no PDF (fundo branco: o PDF é impresso). */
function paraImagem(): string | null {
  try {
    return chart ? chart.toBase64Image('image/png', 1) : null
  } catch {
    return null
  }
}
defineExpose({ paraImagem })

onMounted(() => {
  desenhar()
  // Redesenha ao trocar o tema — a moldura muda, as séries não.
  if (typeof MutationObserver !== 'undefined') {
    observer = new MutationObserver(desenhar)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  }
})

watch(() => props.spec, desenhar, { deep: true })

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.destroy()
  chart = null
})
</script>

<template>
  <figure class="rounded-xl border border-border bg-background p-3 m-0">
    <figcaption class="text-[11px] font-bold uppercase tracking-wide text-muted-foreground mb-2">
      {{ spec.titulo }}
    </figcaption>

    <!-- Rosca: canvas fixo (só as fatias) + legenda em HTML, que responde ao tema de verdade -->
    <div v-if="ehRosca" class="flex items-center gap-4">
      <div class="shrink-0" style="width: 140px; height: 140px;">
        <canvas ref="canvasRef" />
      </div>
      <ul class="space-y-2 m-0 p-0 list-none min-w-0">
        <li v-for="item in legendaRosca" :key="item.rotulo" class="flex items-center gap-2 min-w-0">
          <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ background: item.cor }" />
          <span class="text-[12px] text-foreground truncate">{{ item.rotulo }}: {{ item.valor }} ({{ item.pct }}%)</span>
        </li>
      </ul>
    </div>

    <div v-else :style="{ height: (spec.tipo === 'barras_h' ? Math.max(140, spec.labels.length * 26 + 40) : 190) + 'px' }">
      <canvas ref="canvasRef" />
    </div>
  </figure>
</template>
