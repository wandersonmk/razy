<script setup lang="ts">
/**
 * Um card temático da resposta do Analista.
 *
 * A cor não é decoração: ela diz o que o card significa. Azul para fato
 * neutro, roxo para a narrativa, verde/amarelo/vermelho para o julgamento
 * (chance de fechamento, gravidade do problema), cinza para dado secundário.
 * Por isso o tom sai do `tipo` + `nivel` que vieram do backend, e não de uma
 * escolha do componente.
 *
 * Os fundos são translúcidos (`/8`, `/10`) em vez de cor sólida: assim o mesmo
 * card funciona sobre o fundo claro e o escuro sem precisar de duas paletas.
 */
import { computed } from 'vue'
import type { CardAnalista as Card } from '~/composables/useAnalista'

const props = defineProps<{ card: Card }>()

type Tom = 'azul' | 'roxo' | 'verde' | 'amarelo' | 'vermelho' | 'cinza'

// Classes escritas por extenso, nunca montadas em tempo de execução: o Tailwind
// varre o código-fonte como TEXTO, então `'border-' + cor` ou
// `.replace('border-','ring-')` não geram nada e o estilo some no build.
const TONS: Record<Tom, { borda: string; fundo: string; titulo: string; icone: string; anel: string }> = {
  azul:     { borda: 'border-blue-500/25',    fundo: 'bg-blue-500/[0.07]',    titulo: 'text-blue-600 dark:text-blue-400',       icone: 'text-blue-500',    anel: 'ring-blue-500/30' },
  roxo:     { borda: 'border-violet-500/25',  fundo: 'bg-violet-500/[0.07]',  titulo: 'text-violet-600 dark:text-violet-400',   icone: 'text-violet-500',  anel: 'ring-violet-500/30' },
  verde:    { borda: 'border-emerald-500/25', fundo: 'bg-emerald-500/[0.07]', titulo: 'text-emerald-600 dark:text-emerald-400', icone: 'text-emerald-500', anel: 'ring-emerald-500/30' },
  amarelo:  { borda: 'border-amber-500/30',   fundo: 'bg-amber-500/[0.08]',   titulo: 'text-amber-600 dark:text-amber-400',     icone: 'text-amber-500',   anel: 'ring-amber-500/30' },
  vermelho: { borda: 'border-rose-500/25',    fundo: 'bg-rose-500/[0.07]',    titulo: 'text-rose-600 dark:text-rose-400',       icone: 'text-rose-500',    anel: 'ring-rose-500/30' },
  cinza:    { borda: 'border-border',         fundo: 'bg-muted/40',           titulo: 'text-foreground',                        icone: 'text-muted-foreground', anel: 'ring-border' }
}

const tom = computed<Tom>(() => {
  const { tipo, nivel } = props.card
  if (tipo === 'visao_geral') return 'azul'
  if (tipo === 'resumo') return 'roxo'
  if (tipo === 'coletado') return 'cinza'
  if (tipo === 'proxima_acao') return 'azul'
  if (tipo === 'interesse') {
    return nivel === 'alta' ? 'verde' : nivel === 'baixa' ? 'vermelho' : 'amarelo'
  }
  if (tipo === 'atencao') {
    // nível baixo aqui significa "sem problema" — verde, não vermelho.
    return nivel === 'alta' ? 'vermelho' : nivel === 'baixa' ? 'verde' : 'amarelo'
  }
  return 'cinza'
})

const estilo = computed(() => TONS[tom.value])

/** Etiqueta de nível — só onde ela carrega julgamento. */
const badge = computed(() => {
  const { tipo, nivel } = props.card
  if (!nivel) return null
  if (tipo === 'interesse') {
    return { texto: `Chance ${nivel === 'media' ? 'média' : nivel}`, tom: tom.value }
  }
  if (tipo === 'atencao' && nivel !== 'baixa') {
    return { texto: nivel === 'alta' ? 'Requer ação' : 'Pendência', tom: tom.value }
  }
  return null
})
</script>

<template>
  <section class="rounded-xl border px-4 py-3.5" :class="[estilo.borda, estilo.fundo]">
    <header class="flex items-center gap-2 mb-2.5">
      <svg class="w-4 h-4 shrink-0" :class="estilo.icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <template v-if="card.tipo === 'visao_geral'"><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18M9 10v10" /></template>
        <template v-else-if="card.tipo === 'resumo'"><path d="M4 6h16M4 12h16M4 18h10" /></template>
        <template v-else-if="card.tipo === 'coletado'"><path d="M20 7h-9M14 17H5" /><circle cx="17" cy="17" r="3" /><circle cx="7" cy="7" r="3" /></template>
        <template v-else-if="card.tipo === 'interesse'"><path d="M3 3v18h18" /><path d="M7 14l4-4 3 3 5-6" /></template>
        <template v-else-if="card.tipo === 'atencao'"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></template>
        <template v-else><path d="M5 12h14M13 6l6 6-6 6" /></template>
      </svg>

      <h4 class="text-[12.5px] font-bold tracking-tight" :class="estilo.titulo">{{ card.titulo }}</h4>

      <span
        v-if="badge"
        class="ml-auto text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded shrink-0"
        :class="[TONS[badge.tom].fundo, TONS[badge.tom].titulo, 'ring-1', TONS[badge.tom].anel]"
      >{{ badge.texto }}</span>
    </header>

    <!-- Pares rótulo/valor: visão geral e dados coletados -->
    <dl v-if="card.campos?.length" class="grid grid-cols-2 gap-x-4 gap-y-2 m-0">
      <div v-for="(c, i) in card.campos" :key="i" class="min-w-0">
        <dt class="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{{ c.rotulo }}</dt>
        <dd class="text-[12.5px] text-foreground m-0 break-words">{{ c.valor }}</dd>
      </div>
    </dl>

    <ul v-if="card.itens?.length" class="space-y-1.5 m-0 p-0 list-none" :class="card.campos?.length ? 'mt-3' : ''">
      <li v-for="(t, i) in card.itens" :key="i" class="flex gap-2 text-[12.5px] text-foreground leading-snug">
        <span class="shrink-0 mt-[7px] w-1 h-1 rounded-full" :class="estilo.icone.replace('text-', 'bg-')" />
        <span class="min-w-0">{{ t }}</span>
      </li>
    </ul>

    <p v-if="card.texto" class="text-[12.5px] text-foreground leading-relaxed m-0" :class="(card.itens?.length || card.campos?.length) ? 'mt-3' : ''">
      {{ card.texto }}
    </p>
  </section>
</template>
