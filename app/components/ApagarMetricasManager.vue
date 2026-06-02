<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMetricas } from '~/composables/useMetricas'

const { apagarTodasMetricas } = useMetricas()

let toast: any
onMounted(async () => {
  toast = await useToastSafe()
})

const showConfirm = ref(false)
const apagando = ref(false)

async function confirmarApagar() {
  apagando.value = true
  try {
    await apagarTodasMetricas()
    toast?.success('Todas as métricas foram apagadas. O Dashboard e os Relatórios estão zerados.')
    showConfirm.value = false
  } catch (e: any) {
    toast?.error(e?.message || 'Erro ao apagar métricas')
  } finally {
    apagando.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <div>
      <h3 class="text-base font-semibold text-foreground">Apagar métricas</h3>
      <p class="text-xs text-muted-foreground mt-0.5">
        Limpa permanentemente todos os dados de métricas do sistema.
      </p>
    </div>

    <!-- Zona de perigo -->
    <div class="rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50/60 dark:bg-red-900/10 p-5">
      <div class="flex items-start gap-3">
        <div class="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center shrink-0">
          <svg class="w-5 h-5 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <h4 class="text-sm font-semibold text-red-700 dark:text-red-400">Zona de perigo</h4>
          <p class="text-xs text-muted-foreground mt-1 leading-relaxed">
            Esta ação <strong class="text-foreground">apaga de vez</strong> todas as métricas registradas até agora —
            tanto do <strong class="text-foreground">Dashboard</strong> quanto dos <strong class="text-foreground">Relatórios</strong>:
          </p>
          <ul class="text-xs text-muted-foreground mt-2 space-y-1 list-disc list-inside">
            <li>Histórico de disparos (enviados, falhas e respostas)</li>
            <li>Envios de follow-up</li>
            <li>Contadores de todas as campanhas (zerados)</li>
            <li>Campanhas já excluídas/arquivadas (removidas de vez)</li>
          </ul>
          <p class="text-xs text-red-600 dark:text-red-400 font-medium mt-2">
            ⚠️ Esta ação é irreversível e não pode ser desfeita.
          </p>

          <button
            @click="showConfirm = true"
            class="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
            Apagar todas as métricas
          </button>
        </div>
      </div>
    </div>

    <ConfirmModal
      :show="showConfirm"
      variant="danger"
      title="Apagar todas as métricas?"
      message="Todos os dados registrados até o momento (disparos, respostas, follow-ups e contadores das campanhas) serão apagados do Dashboard e dos Relatórios. Esta ação é irreversível e não pode ser desfeita."
      confirm-text="Sim, apagar tudo"
      cancel-text="Cancelar"
      :loading="apagando"
      @confirm="confirmarApagar"
      @cancel="showConfirm = false"
    />
  </div>
</template>
