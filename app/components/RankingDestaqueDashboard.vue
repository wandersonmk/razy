<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRelatorioAtendimento } from '~/composables/useRelatorioAtendimento'

const { metricas, isLoading, fetchMetricas } = useRelatorioAtendimento()

onMounted(() => { fetchMetricas(30) })

const top3 = computed(() =>
  [...metricas.value]
    .filter((m) => m.atendimentos > 0)
    .sort((a, b) => b.atendimentos - a.atendimentos)
    .slice(0, 3)
)

const MEDALHA = ['🥇', '🥈', '🥉']
const AVATAR: Record<number, string> = {
  0: 'bg-gradient-to-br from-amber-300 via-yellow-400 to-amber-500',
  1: 'bg-gradient-to-br from-slate-300 via-slate-400 to-slate-500',
  2: 'bg-gradient-to-br from-orange-400 via-orange-500 to-amber-700'
}

function iniciais(nome: string): string {
  const partes = (nome || '?').trim().split(/\s+/)
  return ((partes[0]?.[0] || '') + (partes[1]?.[0] || '')).toUpperCase()
}
</script>

<template>
  <div class="bg-card border border-border rounded-xl p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-semibold text-foreground flex items-center gap-1.5">🏆 Top atendentes</h3>
      <NuxtLink to="/relatorios?aba=ranking" class="text-xs text-primary hover:underline">Ver ranking completo →</NuxtLink>
    </div>

    <div v-if="isLoading" class="text-center py-6 text-muted-foreground text-sm">Carregando...</div>

    <div v-else-if="!top3.length" class="text-center py-6">
      <p class="text-sm text-muted-foreground">Ninguém atendeu nos últimos 30 dias ainda.</p>
    </div>

    <div v-else class="space-y-3">
      <div v-for="(m, idx) in top3" :key="m.profissional_id" class="flex items-center gap-3">
        <span class="text-lg w-6 text-center shrink-0">{{ MEDALHA[idx] }}</span>
        <div class="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 shadow" :class="AVATAR[idx]">
          {{ iniciais(m.profissional_nome) }}
        </div>
        <p class="flex-1 min-w-0 text-sm font-medium text-foreground truncate">{{ m.profissional_nome }}</p>
        <p class="text-sm font-bold tabular-nums text-foreground shrink-0">{{ m.atendimentos }} <span class="text-xs font-normal text-muted-foreground">atend.</span></p>
      </div>
    </div>
  </div>
</template>
