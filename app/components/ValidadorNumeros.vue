<template>
  <div class="space-y-6">
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Ação -->
    <div v-if="etapa !== 'upload'" class="flex items-center justify-end p-4 border-b border-border">
      <button
        @click="reset"
        class="flex items-center gap-2 px-4 py-2 border border-border hover:bg-muted text-foreground rounded-lg transition-colors text-sm font-medium"
      >
        <Icon icon="redo" class-name="w-4 h-4" fallback="↺" />
        <span>Recomeçar</span>
      </button>
    </div>

    <div class="p-6">
      <!-- Erro -->
      <div v-if="erro" class="mb-4 px-4 py-3 rounded-lg bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 text-sm">
        {{ erro }}
      </div>

      <!-- ETAPA 1: Upload -->
      <div v-if="etapa === 'upload'">
        <label
          @dragover.prevent="dragOver = true"
          @dragleave.prevent="dragOver = false"
          @drop.prevent="onDrop"
          :class="[
            'flex flex-col items-center justify-center gap-3 w-full py-16 px-6 border-2 border-dashed rounded-xl cursor-pointer transition-colors',
            dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-muted/30'
          ]"
        >
          <Icon icon="file-excel" class-name="w-12 h-12 text-green-600" fallback="📄" />
          <div class="text-center">
            <p class="text-foreground font-medium">Arraste a planilha aqui ou clique para selecionar</p>
            <p class="text-sm text-muted-foreground mt-1">Formatos aceitos: .xlsx, .xls, .csv</p>
          </div>
          <input type="file" accept=".xlsx,.xls,.csv" class="hidden" @change="onFileChange" />
        </label>
        <p class="text-xs text-muted-foreground mt-3 text-center">
          💡 Dica: valide listas menores (ex.: até 1.000–2.000 por vez). Fica mais rápido e protege a reputação do seu número no WhatsApp.
        </p>
      </div>

      <!-- ETAPA 2: Preview / escolher coluna -->
      <div v-else-if="etapa === 'preview'" class="space-y-5">
        <div class="flex flex-wrap items-end gap-4">
          <div class="flex-1 min-w-[200px]">
            <p class="text-sm text-muted-foreground">Arquivo</p>
            <p class="text-foreground font-medium truncate">{{ nomeArquivo }} · {{ linhas.length }} linha(s)</p>
          </div>
          <div class="min-w-[240px]">
            <label class="block text-sm font-medium text-foreground mb-2">Coluna do telefone</label>
            <select
              :value="colunaTelefone"
              @change="setColunaTelefone(Number(($event.target as HTMLSelectElement).value))"
              class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option v-for="c in colunasDisponiveis" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <button
            @click="validar"
            class="flex items-center gap-2 px-5 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition text-sm font-medium"
          >
            <Icon icon="check-circle" class-name="w-4 h-4" fallback="✓" />
            <span>Validar números</span>
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-3 text-xs">
          <span class="text-muted-foreground">⏱️ Tempo estimado: <strong class="text-foreground">{{ estimativaPreview }}</strong></span>
          <span v-if="listaGrande" class="px-2.5 py-1 rounded-md bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
            ⚠️ Lista grande — o ideal é dividir em partes menores (mais rápido e mais seguro para a reputação do número).
          </span>
        </div>

        <!-- Amostra -->
        <div class="overflow-x-auto border border-border rounded-lg">
          <table class="w-full text-sm">
            <thead class="bg-muted">
              <tr>
                <th
                  v-for="(h, i) in headers" :key="i"
                  :class="['text-left py-2 px-3 font-medium text-xs whitespace-nowrap', i === colunaTelefone ? 'text-primary' : 'text-muted-foreground']"
                >
                  {{ h || `Coluna ${i + 1}` }}<span v-if="i === colunaTelefone"> · telefone</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(linha, r) in linhas.slice(0, 5)" :key="r" class="border-t border-border/50">
                <td
                  v-for="(h, i) in headers" :key="i"
                  :class="['py-2 px-3 text-xs whitespace-nowrap', i === colunaTelefone ? 'text-foreground font-mono' : 'text-muted-foreground']"
                >
                  {{ linha[i] ?? '' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="text-xs text-muted-foreground">Mostrando as 5 primeiras linhas para conferência.</p>
      </div>

      <!-- ETAPA 3: Validando -->
      <div v-else-if="etapa === 'validando'" class="py-12 text-center space-y-4">
        <Icon icon="spinner" class-name="w-10 h-10 text-primary mx-auto animate-spin" fallback="⏳" />
        <p class="text-foreground font-medium">Verificando números no WhatsApp...</p>
        <div class="max-w-md mx-auto">
          <div class="h-2 rounded-full bg-muted overflow-hidden">
            <div class="h-full bg-primary transition-all" :style="{ width: pctProgresso + '%' }"></div>
          </div>
          <p class="text-xs text-muted-foreground mt-2">{{ progresso.feitos }} / {{ progresso.total }} números únicos verificados</p>
          <p v-if="etaSegundos" class="text-sm text-foreground mt-1">Tempo restante estimado: <strong>{{ etaTexto }}</strong></p>
          <p class="text-xs text-muted-foreground mt-1">Mantenha esta aba aberta até terminar.</p>
        </div>
        <button
          @click="cancelar"
          :disabled="cancelando"
          class="mt-2 inline-flex items-center gap-2 px-4 py-2 border border-border hover:bg-muted disabled:opacity-60 text-foreground rounded-lg transition-colors text-sm font-medium"
        >
          <Icon :icon="cancelando ? 'spinner' : 'times'" :class-name="cancelando ? 'w-4 h-4 animate-spin' : 'w-4 h-4'" fallback="✕" />
          <span>{{ cancelando ? 'Cancelando…' : 'Cancelar validação' }}</span>
        </button>
        <p class="text-xs text-muted-foreground mt-2 max-w-md mx-auto">
          {{ cancelando
            ? 'Aguardando o lote atual terminar… os números já validados serão entregues.'
            : 'Ao cancelar, os números já validados são entregues e o restante da verificação é interrompido.' }}
        </p>
      </div>

      <!-- ETAPA 4: Resultado -->
      <div v-else-if="etapa === 'resultado'" class="space-y-6">
        <!-- Cards -->
        <div class="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <div class="rounded-xl border border-border p-4">
            <p class="text-2xl font-bold tabular-nums text-foreground">{{ (validos.length + invalidos.length).toLocaleString('pt-BR') }}</p>
            <p class="text-xs text-muted-foreground mt-1">Total de linhas</p>
          </div>
          <div class="rounded-xl border border-green-800/20 bg-green-950/5 p-4">
            <p class="text-2xl font-bold tabular-nums text-green-500">{{ validos.length.toLocaleString('pt-BR') }}</p>
            <p class="text-xs text-muted-foreground mt-1">Com WhatsApp (válidos)</p>
          </div>
          <div class="rounded-xl border border-red-800/20 bg-red-950/5 p-4">
            <p class="text-2xl font-bold tabular-nums text-red-500">{{ invalidos.length.toLocaleString('pt-BR') }}</p>
            <p class="text-xs text-muted-foreground mt-1">Sem WhatsApp (removidos)</p>
          </div>
        </div>

        <p v-if="canalUsado" class="text-xs text-muted-foreground -mt-2">Verificado pelo canal {{ canalUsado }}.</p>

        <div v-if="aviso" class="px-4 py-3 rounded-lg bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 text-sm">
          {{ aviso }}
        </div>

        <!-- Downloads -->
        <div class="flex flex-wrap gap-3">
          <button
            @click="baixar('validos')"
            :disabled="!validos.length"
            class="flex items-center gap-2 px-5 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg transition-colors text-sm font-medium"
          >
            <Icon icon="download" class-name="w-4 h-4" fallback="⬇" />
            <span>Baixar válidos ({{ validos.length }})</span>
          </button>
          <button
            @click="baixar('invalidos')"
            :disabled="!invalidos.length"
            class="flex items-center gap-2 px-5 py-2.5 bg-muted hover:bg-muted/70 disabled:opacity-50 text-foreground border border-border rounded-lg transition-colors text-sm font-medium"
          >
            <Icon icon="download" class-name="w-4 h-4" fallback="⬇" />
            <span>Baixar inválidos ({{ invalidos.length }})</span>
          </button>
        </div>

        <!-- Listas -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h3 class="text-sm font-semibold text-foreground mb-2">Válidos (com WhatsApp)</h3>
            <div class="border border-border rounded-lg max-h-80 overflow-y-auto">
              <table class="w-full text-sm">
                <thead class="bg-muted sticky top-0">
                  <tr>
                    <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Número</th>
                    <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Nome no WhatsApp</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in validos.slice(0, 200)" :key="r.indice" class="border-t border-border/50">
                    <td class="py-1.5 px-3 font-mono text-xs text-foreground whitespace-nowrap">{{ r.numeroOriginal }}</td>
                    <td class="py-1.5 px-3 text-xs text-muted-foreground truncate">{{ r.verifiedName || '—' }}</td>
                  </tr>
                  <tr v-if="!validos.length"><td colspan="2" class="py-4 px-3 text-center text-xs text-muted-foreground">Nenhum</td></tr>
                </tbody>
              </table>
            </div>
            <p v-if="validos.length > 200" class="text-xs text-muted-foreground mt-1">Mostrando 200 de {{ validos.length }} — o download traz todos.</p>
          </div>

          <div>
            <h3 class="text-sm font-semibold text-foreground mb-2">Removidos (sem WhatsApp)</h3>
            <div class="border border-border rounded-lg max-h-80 overflow-y-auto">
              <table class="w-full text-sm">
                <thead class="bg-muted sticky top-0">
                  <tr>
                    <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Número</th>
                    <th class="text-left py-2 px-3 font-medium text-muted-foreground text-xs">Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in invalidos.slice(0, 200)" :key="r.indice" class="border-t border-border/50">
                    <td class="py-1.5 px-3 font-mono text-xs text-foreground whitespace-nowrap">{{ r.numeroOriginal || '—' }}</td>
                    <td class="py-1.5 px-3 text-xs text-muted-foreground">{{ r.motivo }}</td>
                  </tr>
                  <tr v-if="!invalidos.length"><td colspan="2" class="py-4 px-3 text-center text-xs text-muted-foreground">Nenhum</td></tr>
                </tbody>
              </table>
            </div>
            <p v-if="invalidos.length > 200" class="text-xs text-muted-foreground mt-1">Mostrando 200 de {{ invalidos.length }} — o download traz todos.</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Histórico de validações -->
  <div v-if="historico.length" class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <div class="flex items-center justify-between p-6 border-b border-border">
      <div>
        <h2 class="text-lg font-semibold text-foreground">Histórico de validações</h2>
        <p class="text-sm text-muted-foreground mt-1">Baixe novamente listas já validadas ou exclua quando não precisar mais.</p>
      </div>
    </div>
    <div class="p-6 space-y-2">
      <div
        v-for="h in historico" :key="h.id"
        class="flex flex-wrap items-center gap-3 p-3 border border-border rounded-lg hover:bg-muted/30 transition-colors"
      >
        <div class="flex-1 min-w-[180px]">
          <p class="text-sm font-medium text-foreground truncate">{{ h.nome_arquivo }}</p>
          <p class="text-xs text-muted-foreground">
            {{ formatarData(h.created_at) }} ·
            <span class="text-green-600">{{ h.validos_count }} válidos</span> ·
            <span class="text-red-500">{{ h.invalidos_count }} sem WhatsApp</span>
          </p>
        </div>
        <button
          @click="baixarHistorico(h.id, 'validos')" :disabled="!h.validos_count"
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-green-600 hover:bg-green-700 disabled:opacity-40 text-white rounded-lg transition-colors"
        >
          <Icon icon="download" class-name="w-3.5 h-3.5" fallback="⬇" />
          Baixar válidos
        </button>
        <button
          @click="baixarHistorico(h.id, 'invalidos')" :disabled="!h.invalidos_count"
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border hover:bg-muted disabled:opacity-40 text-foreground rounded-lg transition-colors"
        >
          <Icon icon="download" class-name="w-3.5 h-3.5" fallback="⬇" />
          Baixar inválidos
        </button>
        <button
          @click="pedirExclusao(h)"
          class="px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
        >
          Excluir
        </button>
      </div>
    </div>
  </div>
  </div>

  <!-- Modal de confirmação de exclusão -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0" enter-to-class="opacity-100"
      leave-active-class="transition duration-100 ease-in" leave-from-class="opacity-100" leave-to-class="opacity-0"
    >
      <div v-if="itemExcluir" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="cancelarExclusao"></div>
        <div class="relative w-full max-w-sm bg-card text-card-foreground rounded-xl border border-border shadow-2xl p-6">
          <div class="flex items-start gap-3">
            <div class="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <Icon icon="trash" class-name="w-5 h-5 text-red-600" fallback="🗑" />
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold text-foreground">Excluir validação</h3>
              <p class="text-sm text-muted-foreground mt-1">
                Excluir <strong class="text-foreground">{{ itemExcluir.nome_arquivo }}</strong> do histórico?
                Esta ação não pode ser desfeita.
              </p>
            </div>
          </div>
          <div class="flex justify-end gap-3 mt-6">
            <button
              @click="cancelarExclusao"
              class="px-4 py-2 text-sm font-medium border border-border hover:bg-muted text-foreground rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              @click="confirmarExclusao"
              class="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Sim, excluir
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

const {
  etapa, nomeArquivo, headers, linhas, colunaTelefone, colunasDisponiveis,
  progresso, validos, invalidos, canalUsado, erro, aviso, etaSegundos, cancelando,
  parseArquivo, setColunaTelefone, validar, baixar, reset, cancelar, snapshotHistorico,
} = useValidadorNumeros()

const { itens: historico, listar, salvar, excluir, baixar: baixarHist } = useHistoricoValidacoes()

const dragOver = ref(false)

const pctProgresso = computed(() =>
  progresso.value.total ? Math.round((progresso.value.feitos / progresso.value.total) * 100) : 0
)

function formatarDuracao(seg: number): string {
  if (!seg || seg < 60) return 'menos de 1 min'
  const min = Math.round(seg / 60)
  if (min < 60) return `~${min} min`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m ? `~${h}h ${m}min` : `~${h}h`
}

// Estimativa antes de validar (≈ 0,4s por número, em lotes sequenciais).
const estimativaPreview = computed(() => formatarDuracao(linhas.value.length * 0.4))
const etaTexto = computed(() => formatarDuracao(etaSegundos.value))
const listaGrande = computed(() => linhas.value.length > 2000)

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) parseArquivo(file)
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) parseArquivo(file)
}

// Carrega o histórico ao abrir a página.
onMounted(listar)

// Salva automaticamente no histórico assim que uma validação termina — assim o
// "Recomeçar" pode limpar a tela sem perder a lista já tratada.
watch(etapa, (v) => {
  if (v === 'resultado') salvar(snapshotHistorico())
})

function formatarData(d: string): string {
  if (!d) return ''
  return new Date(d).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function baixarHistorico(id: string, tipo: 'validos' | 'invalidos') {
  baixarHist(id, tipo)
}

// Modal de confirmação de exclusão.
const itemExcluir = ref<any>(null)
function pedirExclusao(item: any) {
  itemExcluir.value = item
}
function cancelarExclusao() {
  itemExcluir.value = null
}
async function confirmarExclusao() {
  const id = itemExcluir.value?.id
  itemExcluir.value = null
  if (id) await excluir(id)
}
</script>
