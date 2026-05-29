<template>
  <div class="space-y-4">
    <!-- Header da seção -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-lg font-semibold text-foreground">Produtos do Cardápio</h3>
        <p class="text-sm text-muted-foreground">{{ produtos.length }} produtos cadastrados</p>
      </div>
      <div class="flex items-center gap-3">
        <!-- Filtro por categoria -->
        <select
          v-model="categoriaFiltro"
          class="px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">Todas as categorias</option>
          <option v-for="categoria in categorias" :key="categoria.id" :value="categoria.id">
            {{ categoria.nome }}
          </option>
        </select>
        
        <button
          @click="mostrarModalProduto = true"
          class="px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm"
        >
          <Icon icon="plus" class-name="w-4 h-4 mr-2" fallback="" />
          Novo Produto
        </button>
      </div>
    </div>

    <!-- Lista de produtos -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="produto in produtosFiltrados"
        :key="produto.id"
        class="bg-card border border-border rounded-lg overflow-hidden hover:shadow-md transition-shadow"
      >
        <!-- Imagem do produto -->
        <div class="aspect-[4/3] bg-muted relative">
          <img
            v-if="produto.foto"
            :src="produto.foto"
            :alt="produto.nome"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full flex items-center justify-center">
            <Icon icon="image" class-name="w-12 h-12 text-muted-foreground" fallback="" />
          </div>
          
          <!-- Badge do tipo -->
          <div class="absolute top-2 left-2">
            <span 
              class="px-2 py-1 rounded-full text-xs font-medium"
              :class="produto.tipo === 'pizza' 
                ? 'bg-orange-100 text-orange-700' 
                : 'bg-blue-100 text-blue-700'"
            >
              {{ produto.tipo === 'pizza' ? 'Pizza' : 'Comum' }}
            </span>
          </div>

          <!-- Status do produto -->
          <div class="absolute top-2 right-2">
            <span 
              class="px-2 py-1 rounded-full text-xs font-medium"
              :class="produto.ativo 
                ? 'bg-green-100 text-green-700' 
                : 'bg-red-100 text-red-700'"
            >
              {{ produto.ativo ? 'Ativo' : 'Inativo' }}
            </span>
          </div>
        </div>

        <!-- Conteúdo do card -->
        <div class="p-4">
          <div class="flex items-start justify-between mb-2">
            <div class="flex-1">
              <h4 class="font-semibold text-foreground mb-1">{{ produto.nome }}</h4>
              <p class="text-sm text-muted-foreground">{{ getNomeCategoria(produto.categoriaId) }}</p>
            </div>
            <div class="text-right">
              <p class="text-lg font-bold text-foreground">
                R$ {{ produto.preco.toFixed(2) }}
              </p>
              <p v-if="produto.tipo === 'pizza'" class="text-xs text-muted-foreground">
                {{ produto.sabores?.length || 0 }} sabor(es)
              </p>
            </div>
          </div>

          <p class="text-sm text-muted-foreground mb-3 line-clamp-2">
            {{ produto.descricao }}
          </p>

          <!-- Informações especiais para pizza -->
          <div v-if="produto.tipo === 'pizza' && produto.tamanhos" class="mb-3">
            <p class="text-xs text-muted-foreground mb-1">Tamanhos disponíveis:</p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="tamanho in produto.tamanhos"
                :key="tamanho.nome"
                class="px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs"
              >
                {{ tamanho.nome }}
              </span>
            </div>
          </div>

          <!-- Complementos -->
          <div v-if="produto.complementos && produto.complementos.length > 0" class="mb-3">
            <p class="text-xs text-muted-foreground mb-1">Complementos disponíveis:</p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="complementoId in produto.complementos.slice(0, 3)"
                :key="complementoId"
                class="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs"
              >
                {{ getNomeComplemento(complementoId) }}
              </span>
              <span
                v-if="produto.complementos.length > 3"
                class="px-2 py-1 bg-muted text-muted-foreground rounded text-xs"
              >
                +{{ produto.complementos.length - 3 }}
              </span>
            </div>
          </div>

          <!-- Ações -->
          <div class="flex items-center gap-2">
            <button
              @click="editarProduto(produto)"
              class="flex-1 px-3 py-2 text-sm bg-muted hover:bg-muted/80 text-foreground rounded-lg transition-colors"
            >
              <Icon icon="edit" class-name="w-4 h-4 mr-2" fallback="" />
              Editar
            </button>
            <button
              @click="toggleStatus(produto)"
              :class="[
                'flex-1 px-3 py-2 text-sm rounded-lg transition-colors',
                produto.ativo
                  ? 'bg-red-100 hover:bg-red-200 text-red-700'
                  : 'bg-green-100 hover:bg-green-200 text-green-700'
              ]"
            >
              <Icon :icon="produto.ativo ? 'eye-slash' : 'eye'" class-name="w-4 h-4 mr-2" fallback="" />
              {{ produto.ativo ? 'Desativar' : 'Ativar' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Card para adicionar novo produto -->
      <div
        @click="mostrarModalProduto = true"
        class="border-2 border-dashed border-muted-foreground/30 rounded-lg p-6 hover:border-primary/50 hover:bg-primary/5 transition-colors cursor-pointer flex flex-col items-center justify-center text-center min-h-[300px]"
      >
        <div class="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-3">
          <Icon icon="plus" class-name="w-6 h-6 text-primary" fallback="" />
        </div>
        <h4 class="font-medium text-foreground mb-1">Novo Produto</h4>
        <p class="text-sm text-muted-foreground">Adicione produtos ao seu cardápio</p>
      </div>
    </div>

    <!-- Modal do produto -->
    <ProdutoModal
      v-if="mostrarModalProduto"
      :produto="produtoEditando"
      @close="fecharModal"
      @salvar="salvarProduto"
    />
  </div>
</template>

<script setup lang="ts">
import type { Produto } from '../../shared/types/cardapio.types'

// Composables
const { 
  categorias, 
  produtos, 
  complementos,
  produtosPorCategoria, 
  editarProduto: editarProdutoStore,
  adicionarProduto
} = useCardapio()

// Estado local
const categoriaFiltro = ref('')
const mostrarModalProduto = ref(false)
const produtoEditando = ref<Produto | null>(null)

// Computed
const produtosFiltrados = computed(() => {
  if (!categoriaFiltro.value) {
    return produtos.value
  }
  return produtosPorCategoria(categoriaFiltro.value)
})

// Funções
const getNomeCategoria = (categoriaId: string) => {
  const categoria = categorias.value.find(c => c.id === categoriaId)
  return categoria?.nome || 'Categoria não encontrada'
}

const getNomeComplemento = (complementoId: string) => {
  const complemento = complementos.value.find(c => c.id === complementoId)
  return complemento?.nome || 'Complemento não encontrado'
}

const editarProduto = (produto: Produto) => {
  produtoEditando.value = produto
  mostrarModalProduto.value = true
}

const toggleStatus = (produto: Produto) => {
  editarProdutoStore(produto.id, { ativo: !produto.ativo })
}

const fecharModal = () => {
  mostrarModalProduto.value = false
  produtoEditando.value = null
}

const salvarProduto = (dadosProduto: Omit<Produto, 'id'>) => {
  if (produtoEditando.value) {
    // Editar produto existente
    editarProdutoStore(produtoEditando.value.id, dadosProduto)
  } else {
    // Criar novo produto
    adicionarProduto(dadosProduto)
  }
  fecharModal()
}
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>

