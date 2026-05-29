<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useCanais, type Canal } from '~/composables/useCanais'

const { canais, isLoading, fetchCanais, desconectar, excluir, renomear } = useCanais()
let toast: any
let syncInterval: ReturnType<typeof setInterval> | null = null

function onVisibilityChange() {
  if (document.visibilityState === 'visible') fetchCanais()
}

onMounted(async () => {
  toast = await useToastSafe()
  await fetchCanais()
  syncInterval = setInterval(() => { fetchCanais() }, 15000)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  if (syncInterval) { clearInterval(syncInterval); syncInterval = null }
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

const showAddModal = ref(false)
const showConnectModal = ref(false)
const canalParaConectar = ref<Canal | null>(null)

const confirmExcluir = ref<{ show: boolean; canal: Canal | null }>({ show: false, canal: null })

const editar = ref<{ show: boolean; canal: Canal | null; nome: string; salvando: boolean }>({
  show: false, canal: null, nome: '', salvando: false
})

function abrirEditar(c: Canal) {
  editar.value = { show: true, canal: c, nome: c.nome, salvando: false }
}

function fecharEditar() {
  editar.value = { show: false, canal: null, nome: '', salvando: false }
}

async function salvarEditar() {
  const nome = editar.value.nome.trim()
  if (!nome) { toast?.warning('Informe um nome'); return }
  if (!editar.value.canal) return
  if (nome === editar.value.canal.nome) { fecharEditar(); return }
  editar.value.salvando = true
  try {
    await renomear(editar.value.canal.id, nome)
    toast?.success('Canal renomeado')
    fecharEditar()
  } catch (e: any) {
    toast?.error(e.message || 'Erro ao renomear')
  } finally {
    editar.value.salvando = false
  }
}

async function confirmarExcluir() {
  if (!confirmExcluir.value.canal) return
  try {
    await excluir(confirmExcluir.value.canal.id)
    toast?.success('Canal removido')
    confirmExcluir.value = { show: false, canal: null }
  } catch {
    toast?.error('Erro ao remover canal')
  }
}

function abrirConectar(c: Canal) {
  canalParaConectar.value = c
  showConnectModal.value = true
}

async function desconectarCanal(c: Canal) {
  try {
    await desconectar(c.id)
    toast?.success('Canal desconectado')
  } catch {
    toast?.error('Erro ao desconectar')
  }
}

function onCanalCriado(canal: Canal) {
  canais.value.unshift(canal)
}

async function onCanalConectado(_canal: Canal) {
  await fetchCanais()
}

const statusConfig: Record<string, { label: string; color: string; dot: string }> = {
  conectado: { label: 'Conectado', color: 'text-green-600 dark:text-green-400', dot: 'bg-green-500' },
  aguardando_qr: { label: 'Aguardando QR', color: 'text-amber-600 dark:text-amber-400', dot: 'bg-amber-500' },
  conectando: { label: 'Conectando', color: 'text-blue-600 dark:text-blue-400', dot: 'bg-blue-500' },
  desconectado: { label: 'Desconectado', color: 'text-red-600 dark:text-red-400', dot: 'bg-red-500' },
  erro: { label: 'Erro', color: 'text-red-600 dark:text-red-400', dot: 'bg-red-500' }
}

function formatTelefone(tel: string | null): string {
  if (!tel) return '—'
  const n = tel.replace(/\D/g, '')
  if (n.length === 13) return `+${n.slice(0, 2)} ${n.slice(2, 4)} ${n.slice(4, 9)}-${n.slice(9)}`
  if (n.length === 12) return `+${n.slice(0, 2)} ${n.slice(2, 4)} ${n.slice(4, 8)}-${n.slice(8)}`
  return tel
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between mb-1">
      <div>
        <h3 class="text-base font-semibold text-foreground">Canais</h3>
        <p class="text-xs text-muted-foreground">{{ canais.length }} canal(is) configurado(s)</p>
      </div>
    </div>

    <div v-if="isLoading" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div v-for="i in 2" :key="i" class="h-24 bg-muted/30 rounded-xl animate-pulse" />
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div
        v-for="c in canais"
        :key="c.id"
        class="flex items-center gap-4 p-4 bg-card border border-border rounded-xl hover:border-primary/40 transition"
      >
        <div class="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center shrink-0">
          <svg class="w-6 h-6 text-green-500" fill="currentColor" viewBox="0 0 24 24">
            <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654z"/>
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-foreground truncate">{{ c.nome }}</p>
          <p v-if="c.telefone" class="text-sm text-muted-foreground">{{ formatTelefone(c.telefone) }}</p>
          <p v-else class="text-sm text-muted-foreground">Canal Nativo</p>
          <div :class="statusConfig[c.status]?.color" class="text-xs flex items-center gap-1 mt-0.5">
            <span :class="statusConfig[c.status]?.dot" class="w-1.5 h-1.5 rounded-full" />
            {{ statusConfig[c.status]?.label }}
          </div>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <span class="text-[10px] font-medium px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
            {{ c.tipo === 'nativo' ? 'Nativo' : c.tipo }}
          </span>

          <!-- Editar nome -->
          <button
            @click="abrirEditar(c)"
            class="p-1.5 text-muted-foreground hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition"
            title="Editar nome"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
          </button>

          <!-- Conectar (quando desconectado) -->
          <button
            v-if="c.status !== 'conectado'"
            @click="abrirConectar(c)"
            class="p-1.5 text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition"
            title="Conectar"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
          </button>

          <!-- Desconectar (quando conectado) -->
          <button
            v-else
            @click="desconectarCanal(c)"
            class="p-1.5 text-amber-600 hover:text-amber-700 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded transition"
            title="Desconectar"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
            </svg>
          </button>

          <!-- Excluir -->
          <button
            @click="confirmExcluir = { show: true, canal: c }"
            class="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition"
            title="Remover"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Card adicionar -->
      <button
        @click="showAddModal = true"
        class="flex items-center gap-4 p-4 border-2 border-dashed border-border rounded-xl hover:border-primary/50 hover:bg-muted/20 transition text-left"
      >
        <div class="w-12 h-12 bg-muted rounded-xl flex items-center justify-center shrink-0">
          <svg class="w-6 h-6 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
        </div>
        <div class="flex-1">
          <p class="font-semibold text-foreground">Adicionar Canal</p>
          <p class="text-xs text-muted-foreground">Conecte um novo número de WhatsApp</p>
        </div>
      </button>
    </div>

    <AddCanalModal :show="showAddModal" @close="showAddModal = false" @created="onCanalCriado" />

    <ConnectCanalModal
      :show="showConnectModal"
      :canal="canalParaConectar"
      @close="showConnectModal = false"
      @connected="onCanalConectado"
    />

    <ConfirmModal
      :show="confirmExcluir.show"
      title="Remover Canal"
      :message="`Remover o canal '${confirmExcluir.canal?.nome}'? A instância será desconectada da UAzAPI.`"
      confirm-text="Remover"
      variant="danger"
      @confirm="confirmarExcluir"
      @cancel="confirmExcluir = { show: false, canal: null }"
    />

    <!-- Modal de edição de nome -->
    <Teleport to="body">
      <div
        v-if="editar.show"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        @click.self="fecharEditar"
      >
        <div class="bg-card border border-border rounded-2xl w-full max-w-sm shadow-2xl overflow-hidden">
          <div class="flex items-start gap-3 p-5 border-b border-border">
            <div class="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center shrink-0">
              <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold text-foreground">Editar nome do canal</h3>
              <p class="text-xs text-muted-foreground">Renomeie o canal no banco de dados</p>
            </div>
            <button @click="fecharEditar" class="text-muted-foreground hover:text-foreground transition shrink-0">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="p-5">
            <label class="block text-sm font-medium text-foreground mb-1">Nome do canal</label>
            <input
              v-model="editar.nome"
              type="text"
              placeholder="Ex: Atendimento Principal"
              autofocus
              @keyup.enter="salvarEditar"
              class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>

          <div class="flex gap-3 p-4 border-t border-border">
            <button @click="fecharEditar" class="flex-1 px-4 py-2 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-muted transition">
              Cancelar
            </button>
            <button
              @click="salvarEditar"
              :disabled="editar.salvando || !editar.nome.trim()"
              class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50"
            >
              {{ editar.salvando ? 'Salvando...' : 'Salvar' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
