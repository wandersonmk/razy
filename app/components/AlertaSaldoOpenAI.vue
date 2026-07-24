<template>
  <!-- Banner fixo no topo do conteúdo: só aparece quando a conta OpenAI está sem saldo.
       Some sozinho ~1min após a recarga (a IA volta a responder e limpa a flag). -->
  <Transition name="alerta-saldo">
    <div
      v-if="semSaldo"
      class="flex items-center gap-3 px-4 sm:px-6 py-2.5 bg-red-600 text-white shadow-sm"
      role="alert"
    >
      <!-- Ícone de alerta pulsante (chama a atenção sem poluir) -->
      <span class="relative flex h-2.5 w-2.5 shrink-0">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-white/70 opacity-75" />
        <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-white" />
      </span>

      <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>

      <p class="flex-1 text-sm font-medium leading-snug">
        Sua conta de IA está <strong class="font-semibold underline decoration-white/40">sem saldo</strong>.
        As mensagens automáticas não estão sendo geradas — por favor, recarregue para normalizar.
      </p>

      <a
        :href="LINK_RECARGA"
        target="_blank"
        rel="noopener noreferrer"
        class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white text-red-700 text-xs sm:text-sm font-semibold hover:bg-red-50 transition-colors"
      >
        Recarregar agora
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M7 17 17 7" /><path d="M7 7h10v10" />
        </svg>
      </a>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { useSaldoOpenAI } from '~/composables/useSaldoOpenAI'

const LINK_RECARGA = 'https://platform.openai.com/settings/organization/billing/overview'

const { semSaldo } = useSaldoOpenAI()
</script>

<style scoped>
.alerta-saldo-enter-active,
.alerta-saldo-leave-active {
  transition: opacity 0.3s ease, max-height 0.3s ease;
  max-height: 120px;
  overflow: hidden;
}
.alerta-saldo-enter-from,
.alerta-saldo-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
