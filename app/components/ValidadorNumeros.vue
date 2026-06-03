<template>
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Header -->
    <div class="flex items-center justify-between p-6 border-b border-border">
      <div>
        <h2 class="text-xl font-semibold text-foreground">Validador de números</h2>
        <p class="text-sm text-muted-foreground mt-1">
          Suba sua planilha, verificamos quais números têm WhatsApp e separamos os válidos dos inválidos.
        </p>
      </div>
      <button
        v-if="etapa !== 'upload'"
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
          <p class="text-xs text-muted-foreground mt-1">Listas grandes podem levar alguns minutos — mantenha esta aba aberta.</p>
        </div>
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
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const {
  etapa, nomeArquivo, headers, linhas, colunaTelefone, colunasDisponiveis,
  progresso, validos, invalidos, canalUsado, erro, aviso,
  parseArquivo, setColunaTelefone, validar, baixar, reset,
} = useValidadorNumeros()

const dragOver = ref(false)

const pctProgresso = computed(() =>
  progresso.value.total ? Math.round((progresso.value.feitos / progresso.value.total) * 100) : 0
)

function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) parseArquivo(file)
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) parseArquivo(file)
}
</script>
