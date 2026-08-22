<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useProfissionais, iaDoProfissionalAtiva, type Profissional } from '~/composables/useProfissionais'
import { useCanais, type Canal } from '~/composables/useCanais'

const { profissionais, isLoading, fetchProfissionais, atualizarProfissional, excluirProfissional } = useProfissionais()
const { desconectar: desconectarCanal } = useCanais()

let toast: any
let syncInterval: ReturnType<typeof setInterval> | null = null

function onVisibilityChange() {
  if (document.visibilityState === 'visible') fetchProfissionais({ silent: true })
}

onMounted(async () => {
  toast = await useToastSafe()
  await fetchProfissionais()
  syncInterval = setInterval(() => { fetchProfissionais({ silent: true }) }, 15000)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  if (syncInterval) { clearInterval(syncInterval); syncInterval = null }
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

const STATUS_BACK_TO_FRONT: Record<string, Canal['status']> = {
  connected: 'conectado',
  qr: 'aguardando_qr',
  connecting: 'conectando',
  disconnected: 'desconectado',
  error: 'erro'
}

function canalStatus(p: Profissional): Canal['status'] {
  return STATUS_BACK_TO_FRONT[p.instancia?.status ?? ''] ?? 'desconectado'
}

const statusConfig: Record<string, { label: string; color: string; dot: string }> = {
  conectado: { label: 'Conectado', color: 'text-green-600 dark:text-green-400', dot: 'bg-green-500' },
  aguardando_qr: { label: 'Aguardando QR', color: 'text-amber-600 dark:text-amber-400', dot: 'bg-amber-500' },
  conectando: { label: 'Conectando', color: 'text-blue-600 dark:text-blue-400', dot: 'bg-blue-500' },
  desconectado: { label: 'Sem canal', color: 'text-muted-foreground', dot: 'bg-muted-foreground/50' },
  erro: { label: 'Erro', color: 'text-red-600 dark:text-red-400', dot: 'bg-red-500' }
}

function formatTelefone(tel: string | null | undefined): string {
  if (!tel) return '—'
  let n = tel.replace(/\D/g, '')
  // Sem código do país (11/10 dígitos = DDD + número) — assume BR pra exibir
  // sempre no mesmo padrão "+55 DDD XXXXX-XXXX".
  if (n.length === 11 || n.length === 10) n = '55' + n
  if (n.length === 13) return `+${n.slice(0, 2)} ${n.slice(2, 4)} ${n.slice(4, 9)}-${n.slice(9)}`
  if (n.length === 12) return `+${n.slice(0, 2)} ${n.slice(2, 4)} ${n.slice(4, 8)}-${n.slice(8)}`
  return tel
}

// Máscara de telefone BR pro campo de edição — mesmo padrão do
// AddProfissionalModal.vue (input livre, sem "+55").
function maskTel(valor: string): string {
  let d = (valor || '').replace(/\D/g, '')
  if (d.length > 11 && d.startsWith('55')) d = d.slice(2)
  d = d.slice(0, 11)
  if (d.length <= 2) return d.length ? `(${d}` : ''
  if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
}

function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/)
  return ((partes[0]?.[0] || '') + (partes[1]?.[0] || '')).toUpperCase()
}

// ── Adicionar ──
const showAddModal = ref(false)
function onProfissionalCriado() {
  fetchProfissionais({ silent: true })
}

// ── Conectar (reaproveita o mesmo modal de QR Code dos Canais) ──
const showConnectModal = ref(false)
const canalParaConectar = ref<Canal | null>(null)

function abrirConectar(p: Profissional) {
  if (!p.instancia) return
  canalParaConectar.value = {
    id: p.instancia.id,
    usuario_id: p.usuario_id,
    nome: p.nome,
    tipo: 'nativo',
    instancia_id: null,
    instancia_token: null,
    telefone: p.instancia.phone,
    status: canalStatus(p),
    uso_notificacao: false,
    created_at: '',
    updated_at: ''
  }
  showConnectModal.value = true
}

async function onCanalConectado() {
  await fetchProfissionais()
}

// ── Link compartilhável (o profissional conecta o próprio WhatsApp) ──
const showLinkModal = ref(false)
const linkInstanciaId = ref<string | null>(null)
const linkNome = ref<string | null>(null)

function abrirLink(p: Profissional) {
  if (!p.instancia) return
  linkInstanciaId.value = p.instancia.id
  linkNome.value = p.nome
  showLinkModal.value = true
}

async function desconectarInstancia(p: Profissional) {
  if (!p.instancia) return
  try {
    await desconectarCanal(p.instancia.id)
    toast?.success('Canal desconectado')
    await fetchProfissionais({ silent: true })
  } catch {
    toast?.error('Erro ao desconectar')
  }
}

// ── Editar nome ──
const editar = ref<{ show: boolean; profissional: Profissional | null; nome: string; telefone: string; salvando: boolean }>({
  show: false, profissional: null, nome: '', telefone: '', salvando: false
})

function abrirEditar(p: Profissional) {
  editar.value = { show: true, profissional: p, nome: p.nome, telefone: maskTel(p.telefone || ''), salvando: false }
}

function onEditarTelefoneInput(valor: string) {
  editar.value.telefone = maskTel(valor)
}

function fecharEditar() {
  editar.value = { show: false, profissional: null, nome: '', telefone: '', salvando: false }
}

async function salvarEditar() {
  const nome = editar.value.nome.trim()
  if (!nome) { toast?.warning('Informe um nome'); return }
  if (!editar.value.profissional) return
  editar.value.salvando = true
  try {
    const telDigitos = editar.value.telefone.replace(/\D/g, '')
    await atualizarProfissional(editar.value.profissional.id, { nome, telefone: telDigitos || null })
    toast?.success('Profissional atualizado')
    fecharEditar()
    await fetchProfissionais({ silent: true })
  } catch (e: any) {
    toast?.error(e.message || 'Erro ao salvar')
  } finally {
    editar.value.salvando = false
  }
}

// ── Excluir ──
const confirmExcluir = ref<{ show: boolean; profissional: Profissional | null }>({ show: false, profissional: null })

async function confirmarExcluir() {
  if (!confirmExcluir.value.profissional) return
  try {
    await excluirProfissional(confirmExcluir.value.profissional.id)
    toast?.success('Profissional removido')
    confirmExcluir.value = { show: false, profissional: null }
  } catch (e: any) {
    confirmExcluir.value = { show: false, profissional: null }
    toast?.error(e?.message || 'Erro ao remover profissional')
  }
}
</script>

<template>
  <div>
    <div class="bg-card border border-border rounded-2xl overflow-hidden mb-6">
      <div class="p-6 pb-5">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 class="text-lg font-bold text-foreground">Profissionais &amp; Canais</h2>
            <p class="text-sm text-muted-foreground mt-0.5">Cada profissional com o próprio número — ele atende pelo celular, o painel só acompanha.</p>
          </div>
          <button
            @click="showAddModal = true"
            class="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Novo profissional
          </button>
        </div>
      </div>
      <div class="h-1.5 bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500" />
    </div>

    <div v-if="isLoading" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div v-for="i in 2" :key="i" class="h-28 bg-muted/30 rounded-xl animate-pulse" />
    </div>

    <div v-else-if="!profissionais.length" class="text-center py-16 bg-card border border-border rounded-2xl">
      <p class="text-foreground font-medium">Nenhum profissional cadastrado</p>
      <p class="text-sm text-muted-foreground mt-1">Cadastre o primeiro e gere o QR Code do WhatsApp dele.</p>
      <button @click="showAddModal = true" class="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition">
        Novo profissional
      </button>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div
        v-for="p in profissionais"
        :key="p.id"
        class="flex items-start gap-4 p-4 bg-card border border-border rounded-xl hover:border-primary/40 transition"
      >
        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shrink-0 text-white font-semibold text-sm">
          {{ iniciais(p.nome) }}
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-foreground truncate">{{ p.nome }}</p>
          <p class="text-sm text-muted-foreground">{{ formatTelefone(p.instancia?.phone || p.telefone) }}</p>
          <div class="flex items-center gap-3 mt-1 flex-wrap">
            <div :class="statusConfig[canalStatus(p)]?.color" class="text-xs flex items-center gap-1">
              <span :class="statusConfig[canalStatus(p)]?.dot" class="w-1.5 h-1.5 rounded-full" />
              {{ statusConfig[canalStatus(p)]?.label }}
            </div>
            <NuxtLink
              :to="`/ia-profissionais?profissional=${p.id}`"
              class="text-xs flex items-center gap-1 px-1.5 py-0.5 rounded"
              :class="iaDoProfissionalAtiva(p) ? 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10' : 'text-muted-foreground bg-muted/40 hover:text-foreground'"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="iaDoProfissionalAtiva(p) ? 'bg-emerald-500' : 'bg-muted-foreground/50'" />
              IA {{ iaDoProfissionalAtiva(p) ? 'ligada' : 'desligada' }}
            </NuxtLink>
          </div>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <button
            @click="abrirEditar(p)"
            class="p-1.5 text-muted-foreground hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition"
            title="Editar"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
          </button>

          <button
            v-if="canalStatus(p) !== 'conectado'"
            @click="abrirConectar(p)"
            class="p-1.5 text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition"
            title="Conectar"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          </button>
          <button
            v-else
            @click="desconectarInstancia(p)"
            class="p-1.5 text-amber-600 hover:text-amber-700 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded transition"
            title="Desconectar"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/></svg>
          </button>

          <button
            v-if="p.instancia && canalStatus(p) !== 'conectado'"
            @click="abrirLink(p)"
            class="p-1.5 text-violet-600 hover:text-violet-700 hover:bg-violet-50 dark:hover:bg-violet-900/20 rounded transition"
            title="Link para o profissional conectar"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 24 24">
              <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
            </svg>
          </button>

          <button
            @click="confirmExcluir = { show: true, profissional: p }"
            class="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition"
            title="Remover"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>
        </div>
      </div>
    </div>

    <AddProfissionalModal :show="showAddModal" @close="showAddModal = false" @created="onProfissionalCriado" />

    <ConnectCanalModal
      :show="showConnectModal"
      :canal="canalParaConectar"
      @close="showConnectModal = false"
      @connected="onCanalConectado"
    />

    <ShareLinkModal
      :show="showLinkModal"
      :instancia-id="linkInstanciaId"
      :nome="linkNome"
      @close="showLinkModal = false"
    />

    <ConfirmModal
      :show="confirmExcluir.show"
      title="Remover profissional"
      :message="`Remover '${confirmExcluir.profissional?.nome}'? Apaga junto a IA dele e o canal (desconecta e remove o WhatsApp na UAzAPI). As conversas e o cliente continuam em Conversas/Clientes, marcados como 'Profissional removido'.`"
      confirm-text="Remover"
      variant="danger"
      @confirm="confirmarExcluir"
      @cancel="confirmExcluir = { show: false, profissional: null }"
    />

    <!-- Modal de edição -->
    <Teleport to="body">
      <div
        v-if="editar.show"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        @click.self="fecharEditar"
      >
        <div class="bg-card border border-border rounded-2xl w-full max-w-sm shadow-2xl overflow-hidden">
          <div class="flex items-start gap-3 p-5 border-b border-border">
            <div class="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center shrink-0">
              <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold text-foreground">Editar profissional</h3>
            </div>
            <button @click="fecharEditar" class="text-muted-foreground hover:text-foreground transition shrink-0">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <div class="p-5 space-y-3">
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Nome</label>
              <input
                v-model="editar.nome"
                type="text"
                autofocus
                @keyup.enter="salvarEditar"
                class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Telefone</label>
              <input
                :value="editar.telefone"
                @input="onEditarTelefoneInput(($event.target as HTMLInputElement).value)"
                type="text"
                inputmode="numeric"
                placeholder="(11) 91460-0243"
                @keyup.enter="salvarEditar"
                class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
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
