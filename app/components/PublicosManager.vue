<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import { usePublicos } from '~/composables/usePublicos'
import { useContatos } from '~/composables/useContatos'
import type { Publico } from '~/composables/usePublicos'
import type { Contato } from '~/composables/useContatos'

const { publicos, isLoading, fetchPublicos, criarPublico, excluirPublico, campanhasDoPublico } = usePublicos()
const { contatos, isLoading: loadingContatos, fetchContatos, importarPlanilha, adicionarContato, excluirContato } = useContatos()

let toast: any
onMounted(async () => {
  toast = await useToastSafe()
  await fetchPublicos()
})

// ── Modal Criar Público ──────────────────────────────────────────────────────
const showModalCriar = ref(false)
const criando = ref(false)
const form = ref({ nome: '', regiao: '', status: 'frio' as 'frio' | 'morno' | 'quente' })
const arquivoSelecionado = ref<File | null>(null)
const previewLinhas = ref<Record<string, any>[]>([])
const previewColunas = ref<string[]>([])
const isDragOver = ref(false)

function abrirModalCriar() {
  form.value = { nome: '', regiao: '', status: 'frio' }
  arquivoSelecionado.value = null
  previewLinhas.value = []
  previewColunas.value = []
  showModalCriar.value = true
}

function onArquivoDrop(e: DragEvent) {
  isDragOver.value = false
  const file = e.dataTransfer?.files[0]
  if (file) processarArquivo(file)
}

function onArquivoInput(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) processarArquivo(file)
}

function processarArquivo(file: File) {
  arquivoSelecionado.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target!.result as ArrayBuffer)
      const workbook = XLSX.read(data, { type: 'array' })
      const sheet = workbook.Sheets[workbook.SheetNames[0]]
      const rows = XLSX.utils.sheet_to_json<Record<string, any>>(sheet, { defval: '' })
      previewLinhas.value = rows
      previewColunas.value = rows.length > 0 ? Object.keys(rows[0]) : []
    } catch {
      toast?.error('Erro ao ler planilha. Use .xlsx ou .csv')
      arquivoSelecionado.value = null
    }
  }
  reader.readAsArrayBuffer(file)
}

async function confirmarCriarPublico() {
  if (!form.value.nome.trim()) {
    toast?.warning('Informe o nome do público')
    return
  }
  criando.value = true
  try {
    const publico = await criarPublico({
      nome: form.value.nome.trim(),
      regiao: form.value.regiao.trim() || undefined,
      status: form.value.status
    })
    if (!publico) throw new Error('Erro ao criar público')

    if (previewLinhas.value.length > 0) {
      const { importados, erros } = await importarPlanilha(publico.id, previewLinhas.value)
      toast?.success(`Público criado! ${importados} contatos importados${erros > 0 ? `, ${erros} ignorados` : ''}`)
    } else {
      toast?.success('Público criado com sucesso!')
    }

    showModalCriar.value = false
    await fetchPublicos()
  } catch (err: any) {
    toast?.error(err.message || 'Erro ao criar público')
  } finally {
    criando.value = false
  }
}

// ── Confirmação genérica ─────────────────────────────────────────────────────
const confirmModal = ref({
  show: false,
  title: '',
  message: '',
  loading: false,
  onConfirm: async () => {}
})

function abrirConfirm(opts: { title: string; message: string; onConfirm: () => Promise<void> | void }) {
  confirmModal.value = { show: true, loading: false, ...opts }
}

async function executarConfirm() {
  confirmModal.value.loading = true
  try {
    await confirmModal.value.onConfirm()
    confirmModal.value.show = false
  } catch {
    /* toast já tratado na função */
  } finally {
    confirmModal.value.loading = false
  }
}

const verificandoVinculo = ref<string | null>(null)

// Modal informativo exibido quando o público não pode ser excluído por estar
// vinculado a campanhas (a FK impede a exclusão e a campanha depende dele).
// `campanhas` aqui guarda só as ATIVAS (arquivadas não são exibidas); quando o
// vínculo é exclusivamente com arquivadas, `somenteArquivadas` muda a mensagem.
const bloqueioModal = ref<{
  show: boolean
  publicoNome: string
  campanhas: { id: string; nome: string }[]
  somenteArquivadas: boolean
}>({ show: false, publicoNome: '', campanhas: [], somenteArquivadas: false })

async function solicitarExcluirPublico(pub: Publico) {
  // Antes de excluir, verifica se o público está vinculado a alguma campanha.
  // Se estiver, é impossível excluir (a campanha — e suas métricas — depende dele).
  verificandoVinculo.value = pub.id
  let campanhas: { id: string; nome: string; arquivada: boolean }[] = []
  try {
    campanhas = await campanhasDoPublico(pub.id)
  } catch {
    toast?.error('Erro ao verificar vínculos do público')
    return
  } finally {
    verificandoVinculo.value = null
  }

  if (campanhas.length > 0) {
    const ativas = campanhas.filter((c) => !c.arquivada)
    bloqueioModal.value = {
      show: true,
      publicoNome: pub.nome,
      campanhas: ativas.map((c) => ({ id: c.id, nome: c.nome })),
      somenteArquivadas: ativas.length === 0
    }
    return
  }

  abrirConfirm({
    title: 'Excluir Público',
    message: `Tem certeza que deseja excluir o público "${pub.nome}" e todos os seus contatos? Esta ação não pode ser desfeita.`,
    onConfirm: async () => {
      try {
        await excluirPublico(pub.id)
        toast?.success('Público excluído')
      } catch {
        toast?.error('Erro ao excluir público')
        throw new Error()
      }
    }
  })
}

// ── Modal Ver Contatos ───────────────────────────────────────────────────────
const showModalContatos = ref(false)
const publicoSelecionado = ref<Publico | null>(null)
const showFormNovoContato = ref(false)
const novoContato = ref({ nome: '', telefone: '', email: '', empresa: '', observacao: '' })
const adicionando = ref(false)

async function abrirContatos(pub: Publico) {
  publicoSelecionado.value = pub
  showModalContatos.value = true
  showFormNovoContato.value = false
  await fetchContatos(pub.id)
}

async function salvarNovoContato() {
  if (!novoContato.value.telefone) {
    toast?.warning('Telefone é obrigatório')
    return
  }
  adicionando.value = true
  try {
    await adicionarContato(publicoSelecionado.value!.id, novoContato.value)
    toast?.success('Contato adicionado')
    novoContato.value = { nome: '', telefone: '', email: '', empresa: '', observacao: '' }
    showFormNovoContato.value = false
    await fetchContatos(publicoSelecionado.value!.id)
    await fetchPublicos()
  } catch {
    toast?.error('Erro ao adicionar contato')
  } finally {
    adicionando.value = false
  }
}

function solicitarRemocao(contato: Contato) {
  abrirConfirm({
    title: 'Remover Contato',
    message: `Deseja remover o contato "${contato.nome || contato.telefone}" deste público?`,
    onConfirm: async () => {
      try {
        await excluirContato(contato.id)
        toast?.success('Contato removido')
        await fetchPublicos()
      } catch {
        toast?.error('Erro ao remover contato')
        throw new Error()
      }
    }
  })
}

const statusConfig = {
  frio:   { label: 'Frio',   color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
  morno:  { label: 'Morno',  color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' },
  quente: { label: 'Quente', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Ação -->
    <div class="flex items-center justify-end">
      <button
        @click="abrirModalCriar"
        class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition text-sm font-medium"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Criar Público
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 3" :key="i" class="h-40 bg-card rounded-xl border border-border animate-pulse"/>
    </div>

    <!-- Empty -->
    <div v-else-if="publicos.length === 0" class="text-center py-16">
      <svg class="w-12 h-12 mx-auto text-muted-foreground/40 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
      </svg>
      <p class="text-muted-foreground">Nenhum público criado ainda</p>
      <p class="text-sm text-muted-foreground/70 mt-1">Clique em "Criar Público" para começar</p>
    </div>

    <!-- Grid de Públicos -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="pub in publicos"
        :key="pub.id"
        class="bg-card border border-border rounded-xl p-5 flex flex-col gap-4 hover:border-primary/40 transition"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-foreground truncate">{{ pub.nome }}</h3>
            <p v-if="pub.regiao" class="text-xs text-muted-foreground mt-0.5">{{ pub.regiao }}</p>
          </div>
          <span :class="['text-xs px-2 py-0.5 rounded-full font-medium shrink-0', statusConfig[pub.status].color]">
            {{ statusConfig[pub.status].label }}
          </span>
        </div>

        <div class="flex items-center gap-2 text-sm text-muted-foreground">
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          <span><strong class="text-foreground">{{ pub.total_contatos }}</strong> contatos</span>
        </div>

        <div class="flex items-center gap-2 pt-1 border-t border-border">
          <button
            @click="abrirContatos(pub)"
            class="flex-1 text-xs px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/70 text-foreground transition text-center"
          >
            Ver Contatos
          </button>
          <button
            @click="solicitarExcluirPublico(pub)"
            :disabled="verificandoVinculo === pub.id"
            class="p-1.5 rounded-lg text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition disabled:opacity-50"
            title="Excluir público"
          >
            <svg v-if="verificandoVinculo === pub.id" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/>
              <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75"/>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- ── Modal Criar Público ── -->
    <Teleport to="body">
      <div v-if="showModalCriar" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div class="bg-card border border-border rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl">
          <div class="flex items-center justify-between p-6 border-b border-border">
            <h3 class="text-lg font-semibold text-foreground">Criar Novo Público</h3>
            <button @click="showModalCriar = false" class="text-muted-foreground hover:text-foreground transition">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="p-6 space-y-4">
            <!-- Nome -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Nome do Público <span class="text-red-500">*</span></label>
              <AppInput v-model="form.nome" placeholder="Ex: Leads zona sul, Clientes inativos..." />
            </div>

            <!-- Região -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Região</label>
              <AppInput v-model="form.regiao" placeholder="Ex: São Paulo, Zona Leste..." />
            </div>

            <!-- Status -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-1">Status do Público</label>
              <select
                v-model="form.status"
                class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="frio">❄️ Frio — pouco interesse</option>
                <option value="morno">🌤️ Morno — interesse médio</option>
                <option value="quente">🔥 Quente — alto interesse</option>
              </select>
            </div>

            <!-- Upload Planilha -->
            <div>
              <label class="block text-sm font-medium text-foreground mb-2">Importar Contatos (opcional)</label>
              <div
                class="border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition"
                :class="isDragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'"
                @dragover.prevent="isDragOver = true"
                @dragleave="isDragOver = false"
                @drop.prevent="onArquivoDrop"
                @click="($refs.fileInput as HTMLInputElement).click()"
              >
                <input ref="fileInput" type="file" accept=".xlsx,.xls,.csv" class="hidden" @change="onArquivoInput" />
                <svg class="w-8 h-8 mx-auto text-muted-foreground/60 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <p v-if="!arquivoSelecionado" class="text-sm text-muted-foreground">
                  Arraste uma planilha ou <span class="text-primary">clique para selecionar</span>
                </p>
                <p v-else class="text-sm text-foreground font-medium">
                  📄 {{ arquivoSelecionado.name }}
                  <span class="block text-muted-foreground font-normal mt-0.5">{{ previewLinhas.length }} contatos encontrados</span>
                </p>
              </div>

              <!-- Preview colunas detectadas -->
              <div v-if="previewColunas.length > 0" class="mt-3 p-3 bg-muted/40 rounded-lg">
                <p class="text-xs font-medium text-foreground mb-1">Colunas detectadas:</p>
                <div class="flex flex-wrap gap-1">
                  <span v-for="col in previewColunas.slice(0, 12)" :key="col" class="text-xs px-2 py-0.5 bg-background border border-border rounded text-muted-foreground">
                    {{ col }}
                  </span>
                  <span v-if="previewColunas.length > 12" class="text-xs text-muted-foreground">+{{ previewColunas.length - 12 }}</span>
                </div>
                <p class="text-xs text-muted-foreground mt-2">
                  Campos mapeados: <strong>Nome</strong>, <strong>Telefone</strong>, <strong>Email</strong>, <strong>Empresa</strong>, <strong>Observação</strong>
                </p>
              </div>
            </div>
          </div>

          <div class="flex gap-3 p-6 border-t border-border">
            <button @click="showModalCriar = false" class="flex-1 px-4 py-2 border border-border rounded-lg text-sm text-foreground hover:bg-muted transition">
              Cancelar
            </button>
            <AppButton @click="confirmarCriarPublico" :disabled="criando || !form.nome" class="flex-1">
              <span v-if="criando">Criando...</span>
              <span v-else>Criar Público</span>
            </AppButton>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Modal Ver Contatos ── -->
    <Teleport to="body">
      <div v-if="showModalContatos" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div class="bg-card border border-border rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl">
          <div class="flex items-center justify-between p-6 border-b border-border shrink-0">
            <div>
              <h3 class="text-lg font-semibold text-foreground">{{ publicoSelecionado?.nome }}</h3>
              <p class="text-sm text-muted-foreground">{{ contatos.length }} contatos</p>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="showFormNovoContato = !showFormNovoContato"
                class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                </svg>
                Adicionar
              </button>
              <button @click="showModalContatos = false" class="text-muted-foreground hover:text-foreground transition">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Form novo contato -->
          <div v-if="showFormNovoContato" class="p-4 border-b border-border bg-muted/20 space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <AppInput v-model="novoContato.nome" placeholder="Nome" />
              <AppInput v-model="novoContato.telefone" placeholder="Telefone *" />
              <AppInput v-model="novoContato.email" placeholder="Email" />
              <AppInput v-model="novoContato.empresa" placeholder="Empresa" />
            </div>
            <AppInput v-model="novoContato.observacao" placeholder="Observação / histórico" />
            <div class="flex gap-2">
              <button @click="showFormNovoContato = false" class="px-3 py-1.5 text-sm border border-border rounded-lg text-foreground hover:bg-muted transition">Cancelar</button>
              <AppButton @click="salvarNovoContato" :disabled="adicionando" class="px-3 py-1.5 text-sm">
                {{ adicionando ? 'Salvando...' : 'Salvar Contato' }}
              </AppButton>
            </div>
          </div>

          <!-- Lista contatos -->
          <div class="overflow-auto flex-1">
            <div v-if="loadingContatos" class="p-8 text-center text-muted-foreground">Carregando...</div>
            <div v-else-if="contatos.length === 0" class="p-8 text-center text-muted-foreground">Nenhum contato neste público</div>
            <table v-else class="w-full text-sm min-w-[900px]">
              <thead class="bg-muted sticky top-0 z-10 border-b border-border">
                <tr>
                  <th class="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">Nome</th>
                  <th class="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">Telefone</th>
                  <th class="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">Email</th>
                  <th class="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">Empresa</th>
                  <th class="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">Etapa</th>
                  <th class="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap min-w-[300px]">Observação</th>
                  <th class="px-4 py-2.5 w-10 sticky right-0 bg-muted"/>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in contatos" :key="c.id" class="border-t border-border hover:bg-muted/20 transition">
                  <td class="px-4 py-2.5 text-foreground whitespace-nowrap">{{ c.nome || '—' }}</td>
                  <td class="px-4 py-2.5 text-foreground font-mono text-xs whitespace-nowrap">{{ c.telefone }}</td>
                  <td class="px-4 py-2.5 text-muted-foreground whitespace-nowrap">{{ c.email || '—' }}</td>
                  <td class="px-4 py-2.5 text-muted-foreground whitespace-nowrap">{{ c.empresa || '—' }}</td>
                  <td class="px-4 py-2.5 text-muted-foreground whitespace-nowrap">{{ c.etapa || '—' }}</td>
                  <td class="px-4 py-2.5 text-muted-foreground">
                    <div class="max-w-md max-h-20 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed">{{ c.observacao || '—' }}</div>
                  </td>
                  <td class="px-4 py-2.5 sticky right-0 bg-card">
                    <button @click="solicitarRemocao(c)" class="text-muted-foreground hover:text-red-500 transition">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Modal de confirmação genérico -->
    <ConfirmModal
      :show="confirmModal.show"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :loading="confirmModal.loading"
      confirm-text="Excluir"
      variant="danger"
      @confirm="executarConfirm"
      @cancel="confirmModal.show = false"
    />

    <!-- Modal: público vinculado a campanhas (não pode excluir) -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="bloqueioModal.show"
          class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          @click.self="bloqueioModal.show = false"
        >
          <div class="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            <!-- Header com ícone -->
            <div class="p-6 flex items-start gap-4">
              <div class="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0">
                <svg class="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="text-base font-semibold text-foreground">Não é possível excluir</h3>
                <p v-if="!bloqueioModal.somenteArquivadas" class="text-sm text-muted-foreground mt-1">
                  O público <strong class="text-foreground">"{{ bloqueioModal.publicoNome }}"</strong> está vinculado
                  {{ bloqueioModal.campanhas.length > 1 ? 'às campanhas abaixo' : 'à campanha abaixo' }}.
                  Exclua {{ bloqueioModal.campanhas.length > 1 ? 'essas campanhas' : 'essa campanha' }} antes de remover o público.
                </p>
                <p v-else class="text-sm text-muted-foreground mt-1">
                  O público <strong class="text-foreground">"{{ bloqueioModal.publicoNome }}"</strong> tem métricas
                  registradas em campanhas já removidas. Para excluí-lo, apague as métricas em
                  <strong class="text-foreground">Configurações → Apagar métricas</strong> primeiro.
                </p>
              </div>
            </div>

            <!-- Lista de campanhas ativas vinculadas -->
            <div v-if="bloqueioModal.campanhas.length > 0" class="px-6 pb-2">
              <ul class="space-y-1.5 max-h-52 overflow-y-auto">
                <li
                  v-for="c in bloqueioModal.campanhas"
                  :key="c.id"
                  class="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm"
                >
                  <svg class="w-4 h-4 text-muted-foreground shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"/>
                  </svg>
                  <span class="text-foreground truncate">{{ c.nome }}</span>
                </li>
              </ul>
            </div>

            <!-- Ações -->
            <div class="flex justify-end p-4 border-t border-border bg-muted/20 mt-2">
              <button
                @click="bloqueioModal.show = false"
                class="px-5 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:opacity-90 transition"
              >
                Entendi
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
