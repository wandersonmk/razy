<template>
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header com ações -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">Gerenciamento do Cardápio</h1>
        <p class="text-muted-foreground">Organize categorias, produtos e complementos</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="mostrarModalCategoria = true"
          class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          <Icon icon="plus" class-name="w-4 h-4 mr-2" fallback="" />
          Nova Categoria
        </button>
        <button
          @click="mostrarModalComplemento = true"
          class="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90 transition-colors"
        >
          <Icon icon="puzzle-piece" class-name="w-4 h-4 mr-2" fallback="" />
          Novo Complemento
        </button>
      </div>
    </div>

    <!-- Cards de métricas -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Total de Produtos -->
      <div class="bg-card border border-border rounded-lg p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground">Total de Produtos</p>
            <p class="text-2xl font-bold text-foreground">{{ produtos.length }}</p>
            <p class="text-xs text-green-600 mt-1">{{ produtos.filter(p => p.ativo).length }} ativos</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
            <Icon icon="utensils" class-name="w-6 h-6 text-white" fallback="" />
          </div>
        </div>
      </div>

      <!-- Total de Categorias -->
      <div class="bg-card border border-border rounded-lg p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground">Categorias</p>
            <p class="text-2xl font-bold text-foreground">{{ categorias.length }}</p>
            <p class="text-xs text-green-600 mt-1">bem organizadas</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-lg flex items-center justify-center">
            <Icon icon="layer-group" class-name="w-6 h-6 text-white" fallback="" />
          </div>
        </div>
      </div>

      <!-- Total de Complementos -->
      <div class="bg-card border border-border rounded-lg p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground">Complementos</p>
            <p class="text-2xl font-bold text-foreground">{{ complementos.length }}</p>
            <p class="text-xs text-blue-600 mt-1">{{ complementos.filter(c => c.disponivel).length }} disponíveis</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Icon icon="puzzle-piece" class-name="w-6 h-6 text-white" fallback="" />
          </div>
        </div>
      </div>

      <!-- Preço Médio -->
      <div class="bg-card border border-border rounded-lg p-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground">Preço Médio</p>
            <p class="text-2xl font-bold text-foreground">R$ {{ precoMedio }}</p>
            <p class="text-xs text-yellow-600 mt-1">valor competitivo</p>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-amber-500 to-amber-600 rounded-lg flex items-center justify-center">
            <Icon icon="dollar-sign" class-name="w-6 h-6 text-white" fallback="" />
          </div>
        </div>
      </div>
    </div>

    <!-- Navegação por abas -->
    <div class="bg-card border border-border rounded-lg">
      <div class="border-b border-border">
        <nav class="-mb-px flex space-x-8 px-6">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="abaAtiva = tab.id"
            :class="[
              'py-4 px-1 border-b-2 font-medium text-sm transition-colors',
              abaAtiva === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            ]"
          >
            <Icon :icon="tab.icone" class-name="w-4 h-4 mr-2" fallback="" />
            {{ tab.nome }}
          </button>
        </nav>
      </div>

      <div class="p-6">
        <!-- Aba Categorias -->
        <div v-if="abaAtiva === 'categorias'">
          <CategoriasList />
        </div>

        <!-- Aba Produtos -->
        <div v-if="abaAtiva === 'produtos'">
          <ProdutosList />
        </div>

        <!-- Aba Complementos -->
        <div v-if="abaAtiva === 'complementos'">
          <ComplementosList />
        </div>
      </div>
    </div>

    <!-- Modals -->
    <CategoriaModal
      v-if="mostrarModalCategoria"
      @close="mostrarModalCategoria = false"
      @salvar="handleSalvarCategoria"
    />

    <ComplementoModal
      v-if="mostrarModalComplemento"
      @close="mostrarModalComplemento = false"
      @salvar="handleSalvarComplemento"
    />
  </div>
</template>

<script setup lang="ts">
import type { Categoria, Complemento } from '../../shared/types/cardapio.types'

// Composables
const { categorias, produtos, complementos, adicionarCategoria, adicionarComplemento } = useCardapio()

// Estado da interface
const abaAtiva = ref('categorias')
const mostrarModalCategoria = ref(false)
const mostrarModalComplemento = ref(false)

// Configuração das abas
const tabs = [
  { id: 'categorias', nome: 'Categorias', icone: 'layer-group' },
  { id: 'produtos', nome: 'Produtos', icone: 'utensils' },
  { id: 'complementos', nome: 'Complementos', icone: 'puzzle-piece' }
]

// Computed
const precoMedio = computed(() => {
  if (produtos.value.length === 0) return '0,00'
  const soma = produtos.value.reduce((acc, produto) => acc + produto.preco, 0)
  const media = soma / produtos.value.length
  return media.toFixed(2).replace('.', ',')
})

// Handlers dos modals
const handleSalvarCategoria = (categoria: Omit<Categoria, 'id'>) => {
  adicionarCategoria(categoria)
  mostrarModalCategoria.value = false
}

const handleSalvarComplemento = (complemento: Omit<Complemento, 'id'>) => {
  adicionarComplemento(complemento)
  mostrarModalComplemento.value = false
}
</script>

