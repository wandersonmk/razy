<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

interface MensagemProgresso { percent: number; texto: string }

interface Props {
  /** Rótulo curto de contexto (qual página/ação), mostrado acima da mensagem. */
  title?: string
  /** @deprecated mantido só por compatibilidade com chamadas antigas — não é mais exibido. */
  description?: string
  icon?: string
  /** Sequência de mensagens por marco de progresso (0-100). Default: mensagens de saúde/cuidado. */
  mensagens?: MensagemProgresso[]
  /** Sinal de "dado real pronto" — enquanto false, a barra simula progresso (nunca passa de 92%
   * sozinha); quando vira true, corre até 100%, segura a mensagem final e emite `concluido`. */
  pronto?: boolean
  mostrarPercentual?: boolean
  rodape?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Carregando',
  description: '',
  icon: 'database',
  mensagens: undefined,
  pronto: false,
  mostrarPercentual: true,
  rodape: 'Preparando sua experiência...'
})

const emit = defineEmits<{ concluido: [] }>()

// Mensagens padrão — tom saúde/cuidado/prevenção, identidade do app.
const MENSAGENS_PADRAO: MensagemProgresso[] = [
  { percent: 0, texto: 'Preparando tudo para você...' },
  { percent: 5, texto: '💙 Cuidar da saúde é cuidar do seu futuro.' },
  { percent: 15, texto: 'Sua saúde merece atenção todos os dias.' },
  { percent: 25, texto: 'Um bom plano começa com boas escolhas.' },
  { percent: 40, texto: 'Estamos preparando as melhores informações para você.' },
  { percent: 55, texto: '🩺 Prevenção também é uma forma de cuidado.' },
  { percent: 70, texto: 'Ter tranquilidade para cuidar de quem você ama faz diferença.' },
  { percent: 85, texto: 'Estamos quase lá...' },
  { percent: 95, texto: 'Só mais alguns instantes.' },
  { percent: 100, texto: '💚 Tudo pronto! Vamos cuidar do que realmente importa.' }
]

const progresso = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

function limparTimer() {
  if (timer) { clearInterval(timer); timer = null }
}

// Progresso "de mentirinha" quando ninguém sabe o valor real: rápido no
// início, desacelera de leve em leve, e nunca passa de 92% sozinho — só
// quem chama o componente (via `pronto`) sabe quando os dados chegaram de
// verdade.
function simular() {
  limparTimer()
  timer = setInterval(() => {
    const atual = progresso.value
    let passo: number
    if (atual < 30) passo = 3 + Math.random() * 4
    else if (atual < 65) passo = 1.2 + Math.random() * 1.4
    else if (atual < 88) passo = 0.4 + Math.random() * 0.5
    else passo = 0.1
    progresso.value = Math.min(92, atual + passo)
    if (progresso.value >= 92) limparTimer()
  }, 220)
}

async function finalizar() {
  limparTimer()
  while (progresso.value < 100) {
    progresso.value = Math.min(100, progresso.value + 7)
    await new Promise((r) => setTimeout(r, 22))
  }
  progresso.value = 100
  await new Promise((r) => setTimeout(r, 850)) // segura a mensagem final na tela
  emit('concluido')
}

onMounted(() => {
  if (props.pronto) finalizar()
  else simular()
})

// Se `pronto` chegar depois (o normal: começa false, o pai avisa quando os
// dados carregarem), interrompe a simulação e corre pro final.
watch(() => props.pronto, (val) => { if (val) finalizar() })

onBeforeUnmount(limparTimer)

const listaMensagens = computed(() => (props.mensagens?.length ? props.mensagens : MENSAGENS_PADRAO))

const mensagemAtual = computed(() => {
  const lista = listaMensagens.value
  let atual = lista[0]?.texto || ''
  for (const m of lista) {
    if (progresso.value >= m.percent) atual = m.texto
    else break
  }
  return atual
})

const percentualExibido = computed(() => Math.round(progresso.value))
</script>

<template>
  <div class="fixed inset-0 bg-background/95 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="w-full max-w-sm bg-card border border-border rounded-2xl shadow-2xl p-8 flex flex-col items-center gap-6">
      <!-- Ícone com pulso suave -->
      <div class="relative shrink-0">
        <div class="absolute inset-0 rounded-2xl bg-primary/25 blur-xl animate-pulse" />
        <div class="relative w-14 h-14 bg-gradient-to-br from-primary to-primary/70 rounded-2xl flex items-center justify-center shadow-lg shadow-primary/30">
          <Icon :icon="icon" class-name="w-7 h-7 text-primary-foreground" fallback="" />
        </div>
      </div>

      <div class="text-center w-full">
        <p class="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2.5">{{ title }}</p>
        <Transition name="fade-msg" mode="out-in">
          <p :key="mensagemAtual" class="text-[15px] font-semibold text-foreground leading-snug min-h-[2.75rem] flex items-center justify-center px-1">
            {{ mensagemAtual }}
          </p>
        </Transition>
      </div>

      <!-- Barra de progresso -->
      <div class="w-full">
        <div v-if="mostrarPercentual" class="flex items-center justify-between mb-1.5">
          <span class="text-[11px] text-muted-foreground">Carregando</span>
          <span class="text-xs font-bold text-primary tabular-nums">{{ percentualExibido }}%</span>
        </div>
        <div class="h-2 w-full bg-muted rounded-full overflow-hidden">
          <div
            class="h-full bg-gradient-to-r from-primary to-primary/60 rounded-full transition-[width] duration-300 ease-out"
            :style="{ width: percentualExibido + '%' }"
          />
        </div>
      </div>

      <p class="text-xs text-muted-foreground text-center">{{ rodape }}</p>
    </div>
  </div>
</template>

<style scoped>
.fade-msg-enter-active,
.fade-msg-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}
.fade-msg-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.fade-msg-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
