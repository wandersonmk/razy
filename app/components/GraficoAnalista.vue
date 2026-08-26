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
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
        plugins: {
          legend: {
            position: 'right',
            labels: { color: m.texto, font: { size: 11 }, usePointStyle: true, pointStyle: 'circle', boxWidth: 8, padding: 12 }
          },
          tooltip
        }
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
    }
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
    <div :style="{ height: (spec.tipo === 'barras_h' ? Math.max(140, spec.labels.length * 26 + 40) : 190) + 'px' }">
      <canvas ref="canvasRef" />
    </div>
  </figure>
</template>
