<template>
  <div class="space-y-4">
    <!-- Header da seção -->
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold text-foreground">Categorias do Cardápio</h3>
      <button
        @click="$emit('novaCategoria')"
        class="px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm"
      >
        <Icon icon="plus" class-name="w-4 h-4 mr-2" fallback="" />
        Nova Categoria
      </button>
    </div>

    <!-- Lista de categorias em grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="categoria in categorias"
        :key="categoria.id"
        class="bg-muted/30 border border-border rounded-lg p-4 hover:bg-muted/50 transition-colors"
      >
        <div class="flex items-start justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
              <Icon :icon="categoria.icone || 'folder'" class-name="w-5 h-5 text-primary" fallback="" />
            </div>
            <div>
              <h4 class="font-medium text-foreground">{{ categoria.nome }}</h4>
              <p class="text-sm text-muted-foreground">{{ categoria.descricao || 'Sem descrição' }}</p>
              <div class="flex items-center gap-2 mt-2">
                <span class="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                  {{ produtosPorCategoria(categoria.id).length }} produtos
                </span>
                <span 
                  class="text-xs px-2 py-1 rounded"
                  :class="categoria.ativa ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                >
                  {{ categoria.ativa ? 'Ativa' : 'Inativa' }}
                </span>
              </div>
            </div>
          </div>
          
          <div class="flex items-center space-x-2">
            <button
              @click="editarCategoria(categoria)"
              class="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
            >
              <Icon icon="edit" class-name="w-4 h-4" fallback="" />
            </button>
            <button
              @click="confirmarRemocao(categoria)"
              class="p-2 text-muted-foreground hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <Icon icon="trash" class-name="w-4 h-4" fallback="" />
            </button>
          </div>
        </div>

        <!-- Lista de produtos da categoria (preview) -->
        <div v-if="produtosPorCategoria(categoria.id).length > 0" class="mt-3 pt-3 border-t border-border">
          <p class="text-xs text-muted-foreground mb-2">Produtos:</p>
          <div class="space-y-1">
            <div
              v-for="produto in produtosPorCategoria(categoria.id).slice(0, 3)"
              :key="produto.id"
              class="flex items-center justify-between text-xs"
            >
              <span class="text-foreground">{{ produto.nome }}</span>
              <span class="text-muted-foreground">R$ {{ produto.preco.toFixed(2) }}</span>
            </div>
            <div 
              v-if="produtosPorCategoria(categoria.id).length > 3"
              class="text-xs text-primary cursor-pointer hover:underline"
              @click="$emit('verProdutos', categoria.id)"
            >
              +{{ produtosPorCategoria(categoria.id).length - 3 }} produtos
            </div>
          </div>
        </div>
      </div>

      <!-- Card para adicionar nova categoria -->
      <div
        @click="$emit('novaCategoria')"
        class="border-2 border-dashed border-muted-foreground/30 rounded-lg p-4 hover:border-primary/50 hover:bg-primary/5 transition-colors cursor-pointer flex flex-col items-center justify-center text-center min-h-[200px]"
      >
        <div class="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-3">
          <Icon icon="plus" class-name="w-6 h-6 text-primary" fallback="" />
        </div>
        <h4 class="font-medium text-foreground mb-1">Nova Categoria</h4>
        <p class="text-sm text-muted-foreground">Organize seus produtos em categorias</p>
      </div>
    </div>

    <!-- Modal de confirmação de remoção -->
    <div 
      v-if="categoriaParaRemover"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click="cancelarRemocao"
    >
      <div 
        class="bg-card border border-border rounded-lg p-6 max-w-md w-full mx-4"
        @click.stop
      >
        <h3 class="text-lg font-semibold text-foreground mb-2">Confirmar Remoção</h3>
        <p class="text-muted-foreground mb-4">
          Tem certeza que deseja remover a categoria "{{ categoriaParaRemover.nome }}"? 
          Esta ação não pode ser desfeita.
        </p>
        <div class="flex items-center gap-3 justify-end">
          <button
            @click="cancelarRemocao"
            class="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancelar
          </button>
          <button
            @click="removerCategoria"
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Remover
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Categoria } from '../../shared/types/cardapio.types'

// Emits
defineEmits<{
  novaCategoria: []
  editarCategoria: [categoria: Categoria]
  verProdutos: [categoriaId: string]
}>()

// Composables
const { categorias, produtosPorCategoria, removerCategoria: removerCategoriaStore } = useCardapio()

// Estado local
const categoriaParaRemover = ref<Categoria | null>(null)

// Funções
const editarCategoria = (categoria: Categoria) => {
  // Por enquanto, apenas log - depois implementaremos o modal de edição
  console.log('Editar categoria:', categoria)
}

const confirmarRemocao = (categoria: Categoria) => {
  categoriaParaRemover.value = categoria
}

const cancelarRemocao = () => {
  categoriaParaRemover.value = null
}

const removerCategoria = () => {
  if (categoriaParaRemover.value) {
    removerCategoriaStore(categoriaParaRemover.value.id)
    categoriaParaRemover.value = null
  }
}
</script>

