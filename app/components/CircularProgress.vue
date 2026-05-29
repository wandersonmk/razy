<template>
  <!-- Gauge embutível (sem card próprio) — o card é montado pelo componente pai -->
  <div class="flex flex-col items-center">
    <div class="relative w-40 h-40 sm:w-44 sm:h-44">
      <svg class="w-full h-full -rotate-90" viewBox="0 0 120 120" style="overflow: visible;" aria-hidden="true">
        <!-- Trilho de fundo -->
        <circle
          cx="60"
          cy="60"
          r="40"
          stroke="currentColor"
          stroke-width="9"
          fill="none"
          class="text-muted/25"
        />
        <!-- Arco de progresso -->
        <circle
          cx="60"
          cy="60"
          r="40"
          stroke="url(#deliveryGradient)"
          stroke-width="9"
          fill="none"
          stroke-linecap="round"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="strokeDashoffset"
          class="transition-[stroke-dashoffset] duration-700 ease-out"
          style="filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.35))"
        />
        <defs>
          <linearGradient id="deliveryGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#06B6D4" />
            <stop offset="50%" style="stop-color:#3B82F6" />
            <stop offset="100%" style="stop-color:#8B5CF6" />
          </linearGradient>
        </defs>
      </svg>

      <!-- Texto central -->
      <div class="absolute inset-0 flex flex-col items-center justify-center">
        <div class="text-4xl font-bold leading-none tabular-nums text-foreground">{{ displayPercentage }}%</div>
        <div class="mt-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{{ label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  /** Total da base (ex.: enviados + falhas) */
  total: number
  /** Parcela atingida (ex.: enviados) */
  value: number
  /** Rótulo exibido abaixo do percentual */
  label?: string
}>(), {
  label: 'Entregues'
})

const radius = 40
const circumference = 2 * Math.PI * radius

const targetPercentage = computed(() => {
  if (!props.total || props.total <= 0) return 0
  return Math.min(100, Math.max(0, (props.value / props.total) * 100))
})

const currentPercentage = ref(0)
const displayPercentage = ref(0)

const strokeDashoffset = computed(
  () => circumference - (currentPercentage.value / 100) * circumference
)

let raf: number | undefined

function animate() {
  if (raf) cancelAnimationFrame(raf)
  const duration = 1200
  const to = targetPercentage.value
  let startTs: number | null = null

  const step = (now: number) => {
    if (startTs === null) startTs = now
    const p = Math.min((now - startTs) / duration, 1)
    const ease = 1 - Math.pow(1 - p, 3)
    currentPercentage.value = to * ease
    displayPercentage.value = Math.round(currentPercentage.value)
    if (p < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
}

onMounted(() => {
  // Respeita prefers-reduced-motion (skill §7 reduced-motion / §10 animation-optional)
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (reduce) {
    currentPercentage.value = targetPercentage.value
    displayPercentage.value = Math.round(targetPercentage.value)
  } else {
    animate()
  }
})

watch(() => [props.value, props.total], () => animate())

onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
})
</script>
