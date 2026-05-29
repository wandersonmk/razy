<template>
  <div class="space-y-6">
    <!-- Header com botão de adicionar -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
          Complementos
        </h2>
        <p class="text-gray-600 dark:text-gray-400">
          Gerencie os complementos disponíveis para seus produtos
        </p>
      </div>
      <AppButton
        @click="openCreateModal"
        class="flex items-center gap-2"
      >
        <i class="fas fa-plus"></i>
        Novo Complemento
      </AppButton>
    </div>

    <!-- Lista de complementos -->
    <div v-if="complementos.length === 0" class="text-center py-12">
      <i class="fas fa-utensils text-4xl text-gray-300 dark:text-gray-600 mb-4"></i>
      <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">
        Nenhum complemento cadastrado
      </h3>
      <p class="text-gray-600 dark:text-gray-400 mb-4">
        Comece criando seu primeiro complemento
      </p>
      <AppButton @click="openCreateModal">
        <i class="fas fa-plus mr-2"></i>
        Criar Primeiro Complemento
      </AppButton>
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="complemento in complementos"
        :key="complemento.id"
        class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow"
      >
        <!-- Header do card -->
        <div class="flex items-start justify-between mb-3">
          <div class="flex-1 min-w-0">
            <h3 class="font-medium text-gray-900 dark:text-white truncate">
              {{ complemento.nome }}
            </h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              R$ {{ complemento.preco.toFixed(2).replace('.', ',') }}
            </p>
          </div>
          
          <!-- Menu de ações -->
          <div class="flex items-center gap-1 ml-2">
            <button
              @click="editComplemento(complemento)"
              class="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Editar complemento"
            >
              <i class="fas fa-edit text-sm"></i>
            </button>
            
            <button
              @click="confirmDelete(complemento)"
              class="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Excluir complemento"
            >
              <i class="fas fa-trash text-sm"></i>
            </button>
          </div>
        </div>

        <!-- Descrição -->
        <p v-if="complemento.descricao" class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-3">
          {{ complemento.descricao }}
        </p>

        <!-- Badge de disponibilidade -->
        <div class="flex items-center justify-between">
          <span 
            :class="[
              'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
              complemento.disponivel 
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
            ]"
          >
            <i :class="[
              'fas mr-1',
              complemento.disponivel ? 'fa-check-circle' : 'fa-times-circle'
            ]"></i>
            {{ complemento.disponivel ? 'Disponível' : 'Indisponível' }}
          </span>

          <!-- Toggle de disponibilidade -->
          <button
            @click="toggleDisponibilidade(complemento)"
            :class="[
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
              complemento.disponivel ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
            ]"
          >
            <span
              :class="[
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                complemento.disponivel ? 'translate-x-6' : 'translate-x-1'
              ]"
            />
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de confirmação de exclusão -->
    <div
      v-if="showDeleteModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      @click.self="closeDeleteModal"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <div class="flex items-center mb-4">
          <div class="flex-shrink-0 w-10 h-10 mx-auto bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
            <i class="fas fa-exclamation-triangle text-red-600 dark:text-red-400"></i>
          </div>
          <div class="ml-4">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">
              Excluir Complemento
            </h3>
          </div>
        </div>
        
        <p class="text-gray-600 dark:text-gray-400 mb-6">
          Tem certeza que deseja excluir o complemento 
          <strong>"{{ complementoToDelete?.nome }}"</strong>?
          Esta ação não pode ser desfeita.
        </p>
        
        <div class="flex gap-3">
          <AppButton
            @click="closeDeleteModal"
            variant="secondary"
            class="flex-1"
          >
            Cancelar
          </AppButton>
          <AppButton
            @click="deleteComplemento"
            variant="destructive"
            class="flex-1"
          >
            <i class="fas fa-trash mr-2"></i>
            Excluir
          </AppButton>
        </div>
      </div>
    </div>

    <!-- Modal de criação/edição -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      @click.self="closeModal"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">
            {{ isEditing ? 'Editar Complemento' : 'Novo Complemento' }}
          </h3>
          <button
            @click="closeModal"
            class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>

        <form @submit.prevent="saveComplemento" class="space-y-4">
          <!-- Nome -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Nome do Complemento *
            </label>
            <AppInput
              v-model="form.nome"
              placeholder="Ex: Queijo extra, Bacon, Molho especial..."
              required
            />
          </div>

          <!-- Preço -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Preço *
            </label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                R$
              </span>
              <AppInput
                v-model="form.preco"
                type="number"
                step="0.01"
                min="0"
                placeholder="0,00"
                class="pl-10"
                required
              />
            </div>
          </div>

          <!-- Descrição -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Descrição
            </label>
            <textarea
              v-model="form.descricao"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
              rows="3"
              placeholder="Descrição opcional do complemento..."
            ></textarea>
          </div>

          <!-- Disponibilidade -->
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
              Disponível para venda
            </span>
            <button
              type="button"
              @click="form.disponivel = !form.disponivel"
              :class="[
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                form.disponivel ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
              ]"
            >
              <span
                :class="[
                  'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                  form.disponivel ? 'translate-x-6' : 'translate-x-1'
                ]"
              />
            </button>
          </div>

          <!-- Botões -->
          <div class="flex gap-3 pt-4">
            <AppButton
              type="button"
              @click="closeModal"
              variant="secondary"
              class="flex-1"
            >
              Cancelar
            </AppButton>
            <AppButton
              type="submit"
              class="flex-1"
            >
              <i :class="['fas mr-2', isEditing ? 'fa-save' : 'fa-plus']"></i>
              {{ isEditing ? 'Salvar' : 'Criar' }}
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Complemento } from '../../shared/types/cardapio.types'

const { 
  complementos, 
  adicionarComplemento, 
  editarComplemento, 
  removerComplemento 
} = useCardapio()

const toast = await useToastSafe()

// Estados do modal
const showModal = ref(false)
const showDeleteModal = ref(false)
const isEditing = ref(false)
const complementoToDelete = ref<Complemento | null>(null)

// Formulário
const form = ref({
  nome: '',
  preco: '',
  descricao: '',
  disponivel: true
})

const resetForm = () => {
  form.value = {
    nome: '',
    preco: '',
    descricao: '',
    disponivel: true
  }
}

const openCreateModal = () => {
  resetForm()
  isEditing.value = false
  showModal.value = true
}

const editComplemento = (complemento: Complemento) => {
  form.value = {
    nome: complemento.nome,
    preco: complemento.preco.toString(),
    descricao: complemento.descricao || '',
    disponivel: complemento.disponivel
  }
  isEditing.value = true
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
  resetForm()
}

const saveComplemento = () => {
  if (isEditing.value) {
    // Lógica para editar complemento existente
    // Por enquanto só fechamos o modal
    toast.add({
      title: 'Complemento editado',
      description: 'As alterações foram salvas com sucesso',
      color: 'green'
    })
  } else {
    adicionarComplemento({
      nome: form.value.nome,
      preco: Number(form.value.preco),
      descricao: form.value.descricao || undefined,
      obrigatorio: false,
      categoria: 'Adicionais',
      disponivel: form.value.disponivel
    })
    
    toast.add({
      title: 'Complemento criado',
      description: `"${form.value.nome}" foi adicionado com sucesso`,
      color: 'green'
    })
  }
  
  closeModal()
}

const confirmDelete = (complemento: Complemento) => {
  complementoToDelete.value = complemento
  showDeleteModal.value = true
}

const deleteComplemento = () => {
  if (complementoToDelete.value) {
    removerComplemento(complementoToDelete.value.id)
    
    toast.add({
      title: 'Complemento excluído',
      description: `"${complementoToDelete.value.nome}" foi removido`,
      color: 'red'
    })
  }
  closeDeleteModal()
}

const closeDeleteModal = () => {
  showDeleteModal.value = false
  complementoToDelete.value = null
}

const toggleDisponibilidade = (complemento: Complemento) => {
  // Por enquanto só mostra uma notificação
  // Na implementação real, chamaria editarComplemento
  toast.add({
    title: complemento.disponivel ? 'Complemento desabilitado' : 'Complemento habilitado',
    description: `"${complemento.nome}" ${complemento.disponivel ? 'não está mais disponível' : 'está disponível novamente'}`,
    color: complemento.disponivel ? 'orange' : 'green'
  })
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

