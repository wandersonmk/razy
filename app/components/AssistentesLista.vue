<template>
  <div>
    <!-- Header -->
    <div class="bg-card border border-border rounded-2xl overflow-hidden mb-6">
      <div class="p-6 pb-5">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 class="text-lg font-bold text-foreground">Assistentes</h2>
            <p class="text-sm text-muted-foreground mt-0.5">Especialistas que atendem em cada número da empresa</p>
          </div>
          <div class="relative w-full sm:w-64">
            <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/></svg>
            <input
              v-model="busca"
              type="text"
              placeholder="Pesquisar por nome..."
              class="w-full pl-9 pr-9 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <button
              v-if="busca"
              type="button"
              @click="busca = ''"
              title="Limpar busca"
              class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md text-muted-foreground hover:bg-muted transition"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
        </div>
      </div>
      <div class="h-1.5 bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500" />
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20 text-muted-foreground text-sm">
      Carregando assistentes...
    </div>

    <!-- Vazio: nenhum assistente cadastrado -->
    <div v-else-if="!assistentes.length" class="text-center py-16 bg-card border border-border rounded-2xl">
      <p class="text-foreground font-medium">Nenhum assistente ainda</p>
      <p class="text-sm text-muted-foreground mt-1">Crie um canal em Configurações — cada canal já nasce com um assistente.</p>
    </div>

    <!-- Vazio: busca sem resultado -->
    <div v-else-if="!assistentesFiltrados.length" class="text-center py-16 bg-card border border-border rounded-2xl">
      <p class="text-foreground font-medium">Nenhum assistente encontrado</p>
      <p class="text-sm text-muted-foreground mt-1">Nada corresponde a “{{ busca }}”.</p>
    </div>

    <!-- Grade de cards -->
    <div v-else class="grid gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
      <AssistenteCard
        v-for="a in assistentesFiltrados"
        :key="a.id"
        :assistente="a"
        @editar="(id) => $emit('editar', id)"
        @toggle="alternarAtivo"
        @excluir="pedirExclusao"
      />
    </div>

    <!-- Confirmar exclusão -->
    <ConfirmModal
      :show="!!aExcluir"
      title="Excluir assistente"
      :message="`Remover o assistente “${aExcluir?.nome || ''}”? A instância vinculada não é afetada — fica livre para outro assistente.`"
      confirm-text="Excluir"
      variant="danger"
      :loading="excluindo"
      @confirm="confirmarExclusao"
      @cancel="aExcluir = null"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAssistentes, type Assistente } from '~/composables/useAssistentes'

defineEmits<{ editar: [id: string] }>()

const { assistentes, isLoading, fetchAssistentes, atualizarAssistente, excluirAssistente } = useAssistentes()

let toast: any

onMounted(async () => {
  toast = await useToastSafe()
  await fetchAssistentes()
})

// ── Busca por nome ──
const busca = ref('')
const assistentesFiltrados = computed(() => {
  const termo = busca.value.trim().toLowerCase()
  if (!termo) return assistentes.value
  return assistentes.value.filter((a) => (a.nome || '').toLowerCase().includes(termo))
})

// ── Ligar / desligar ──
async function alternarAtivo(a: Assistente) {
  const alvo = !a.ativo
  a.ativo = alvo // otimista
  try {
    await atualizarAssistente(a.id, { ativo: alvo })
    toast?.success(alvo ? 'Assistente ligado' : 'Assistente desligado')
  } catch (e: any) {
    a.ativo = !alvo // reverte
    toast?.error(e?.message || 'Erro ao alterar status')
  }
}

// ── Excluir ──
const aExcluir = ref<Assistente | null>(null)
const excluindo = ref(false)
function pedirExclusao(a: Assistente) { aExcluir.value = a }
async function confirmarExclusao() {
  if (!aExcluir.value) return
  excluindo.value = true
  try {
    await excluirAssistente(aExcluir.value.id)
    toast?.success('Assistente excluído')
    aExcluir.value = null
  } catch (e: any) {
    toast?.error(e?.message || 'Erro ao excluir')
  } finally {
    excluindo.value = false
  }
}
</script>
