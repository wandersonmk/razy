<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { formatarDuracaoSegundos, useRelatorioAtendimento, type MetricaProfissional } from '~/composables/useRelatorioAtendimento'

const { metricas, isLoading, fetchMetricas } = useRelatorioAtendimento()
const dias = ref(30)

type Categoria = 'atendimentos' | 'tmpr'
const categoria = ref<Categoria>('atendimentos')
let festejado = false

async function carregar() {
  await fetchMetricas(dias.value)
  if (!festejado && elegiveis.value.length >= 1) {
    festejado = true
    comemorar()
  }
}

onMounted(carregar)
watch(dias, carregar)

// Só entra no ranking quem de fato tem o dado que está sendo comparado —
// "mais atendimentos" não rankeia quem ainda não atendeu ninguém, e "resposta
// mais rápida" não rankeia quem nunca teve 1ª resposta registrada.
const elegiveis = computed(() => {
  if (categoria.value === 'atendimentos') return metricas.value.filter((m) => m.atendimentos > 0)
  return metricas.value.filter((m) => m.tmpr_seg !== null)
})

const ranking = computed(() => {
  const lista = [...elegiveis.value]
  if (categoria.value === 'atendimentos') lista.sort((a, b) => b.atendimentos - a.atendimentos)
  else lista.sort((a, b) => (a.tmpr_seg ?? 0) - (b.tmpr_seg ?? 0))
  return lista
})

const podio = computed(() => ranking.value.slice(0, 3))
const resto = computed(() => ranking.value.slice(3))
const lider = computed(() => ranking.value[0] || null)

function valorPrincipal(m: MetricaProfissional): string {
  return categoria.value === 'atendimentos'
    ? m.atendimentos.toLocaleString('pt-BR')
    : formatarDuracaoSegundos(m.tmpr_seg)
}

const valorLabel = computed(() => (categoria.value === 'atendimentos' ? 'atendimentos' : 'até 1ª resposta'))

// Barra do restante da lista, relativa ao líder — pra "resposta mais rápida"
// (menor é melhor) inverte a proporção, senão o mais lento pareceria o maior.
function proporcao(m: MetricaProfissional): number {
  if (!lider.value) return 0
  if (categoria.value === 'atendimentos') {
    return lider.value.atendimentos > 0 ? (m.atendimentos / lider.value.atendimentos) * 100 : 0
  }
  const liderSeg = lider.value.tmpr_seg || 1
  const meuSeg = m.tmpr_seg || liderSeg
  return meuSeg > 0 ? Math.min(100, (liderSeg / meuSeg) * 100) : 0
}

function iniciais(nome: string): string {
  const partes = (nome || '?').trim().split(/\s+/)
  return ((partes[0]?.[0] || '') + (partes[1]?.[0] || '')).toUpperCase()
}

const PLACE_STYLE: Record<number, { ordem: string; altura: string; avatar: string; bloco: string; medalha: string; texto: string }> = {
  1: { ordem: 'order-2', altura: 'h-28', avatar: 'bg-gradient-to-br from-amber-300 via-yellow-400 to-amber-500 ring-4 ring-amber-300/40', bloco: 'bg-gradient-to-t from-amber-500 to-yellow-400', medalha: '🥇', texto: 'text-amber-500' },
  2: { ordem: 'order-1', altura: 'h-20', avatar: 'bg-gradient-to-br from-slate-300 via-slate-400 to-slate-500 ring-4 ring-slate-300/40', bloco: 'bg-gradient-to-t from-slate-500 to-slate-300', medalha: '🥈', texto: 'text-slate-400' },
  3: { ordem: 'order-3', altura: 'h-14', avatar: 'bg-gradient-to-br from-orange-400 via-orange-500 to-amber-700 ring-4 ring-orange-400/40', bloco: 'bg-gradient-to-t from-amber-800 to-orange-500', medalha: '🥉', texto: 'text-orange-500' }
}

async function comemorar() {
  if (typeof window === 'undefined') return
  try {
    const confetti = (await import('canvas-confetti')).default
    const cores = ['#f59e0b', '#a855f7', '#22c55e', '#3b82f6']
    confetti({ particleCount: 70, spread: 65, startVelocity: 38, origin: { y: 0.6, x: 0.5 }, colors: cores })
    setTimeout(() => confetti({ particleCount: 40, spread: 100, startVelocity: 28, origin: { y: 0.55, x: 0.3 }, colors: cores }), 150)
    setTimeout(() => confetti({ particleCount: 40, spread: 100, startVelocity: 28, origin: { y: 0.55, x: 0.7 }, colors: cores }), 250)
  } catch {
    // efeito puramente cosmético — nunca deve quebrar a tela
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between gap-3 flex-wrap p-6 border-b border-border">
      <div>
        <h3 class="text-base font-semibold text-foreground flex items-center gap-2">
          <span>🏆</span> Ranking de atendentes
        </h3>
        <p class="text-sm text-muted-foreground mt-0.5">Quem mais atende e quem responde mais rápido — no período selecionado.</p>
      </div>
      <select
        v-model.number="dias"
        class="px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
      >
        <option :value="7">Últimos 7 dias</option>
        <option :value="30">Últimos 30 dias</option>
        <option :value="90">Últimos 90 dias</option>
      </select>
    </div>

    <!-- Categoria -->
    <div class="px-6 pt-5 flex justify-center">
      <div class="inline-flex p-1 rounded-xl bg-muted/50 border border-border gap-1">
        <button
          @click="categoria = 'atendimentos'"
          :class="['px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-1.5', categoria === 'atendimentos' ? 'bg-card shadow text-foreground' : 'text-muted-foreground hover:text-foreground']"
        >
          🏆 Mais atendimentos
        </button>
        <button
          @click="categoria = 'tmpr'"
          :class="['px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-1.5', categoria === 'tmpr' ? 'bg-card shadow text-foreground' : 'text-muted-foreground hover:text-foreground']"
        >
          ⚡ Resposta mais rápida
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="text-center py-16 text-muted-foreground text-sm">Carregando ranking...</div>

    <div v-else-if="!ranking.length" class="text-center py-16 px-6">
      <p class="text-4xl mb-3">🏁</p>
      <p class="text-foreground font-medium">Ainda sem dados suficientes pra montar o pódio</p>
      <p class="text-sm text-muted-foreground mt-1">
        {{ categoria === 'atendimentos' ? 'Assim que os profissionais começarem a atender, o ranking aparece aqui.' : 'Precisa de pelo menos uma 1ª resposta registrada no período.' }}
      </p>
    </div>

    <template v-else>
      <!-- Pódio -->
      <div class="px-6 pt-8 pb-2">
        <div class="flex items-end justify-center gap-3 sm:gap-6 max-w-lg mx-auto">
          <div
            v-for="(m, idx) in podio"
            :key="m.profissional_id"
            class="flex flex-col items-center flex-1 min-w-0 animate-in fade-in slide-in-from-bottom-4 duration-500"
            :class="PLACE_STYLE[idx + 1].ordem"
            :style="{ animationDelay: `${idx * 90}ms` }"
          >
            <div class="relative mb-2">
              <svg v-if="idx === 0" class="absolute -top-7 left-1/2 -translate-x-1/2 w-7 h-7 text-amber-400 drop-shadow animate-bounce" fill="currentColor" viewBox="0 0 24 24">
                <path d="M5 16L3 6l5.5 4L12 4l3.5 6L21 6l-2 10H5zm0 2h14v2H5v-2z"/>
              </svg>
              <div
                class="rounded-full flex items-center justify-center text-white font-bold shadow-lg shrink-0"
                :class="[PLACE_STYLE[idx + 1].avatar, idx === 0 ? 'w-16 h-16 text-lg' : 'w-12 h-12 text-sm']"
              >
                {{ iniciais(m.profissional_nome) }}
              </div>
              <span class="absolute -bottom-1 -right-1 text-lg leading-none">{{ PLACE_STYLE[idx + 1].medalha }}</span>
            </div>
            <p class="font-semibold text-sm text-foreground truncate max-w-[100px] text-center">{{ m.profissional_nome }}</p>
            <p class="text-lg font-bold tabular-nums" :class="PLACE_STYLE[idx + 1].texto">{{ valorPrincipal(m) }}</p>
            <p class="text-[10px] text-muted-foreground mb-2">{{ valorLabel }}</p>
            <div
              class="w-full rounded-t-lg flex items-start justify-center pt-2 shadow-inner"
              :class="[PLACE_STYLE[idx + 1].altura, PLACE_STYLE[idx + 1].bloco]"
            >
              <span class="text-2xl font-black text-white/85">{{ idx + 1 }}º</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Restante do ranking -->
      <div v-if="resto.length" class="px-6 pb-6 pt-4">
        <div class="max-w-lg mx-auto space-y-1.5">
          <div
            v-for="(m, idx) in resto"
            :key="m.profissional_id"
            class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/40 transition"
          >
            <span class="w-6 text-center text-xs font-semibold text-muted-foreground shrink-0">{{ idx + 4 }}º</span>
            <div class="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center text-white text-[11px] font-semibold shrink-0">
              {{ iniciais(m.profissional_nome) }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2">
                <p class="text-sm font-medium text-foreground truncate">{{ m.profissional_nome }}</p>
                <p class="text-sm font-semibold tabular-nums text-foreground shrink-0">{{ valorPrincipal(m) }}</p>
              </div>
              <div class="h-1.5 bg-muted rounded-full overflow-hidden mt-1">
                <div class="h-full bg-primary/60 rounded-full transition-all duration-700" :style="{ width: proporcao(m) + '%' }" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
