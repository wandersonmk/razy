<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  email: string
}>()

const emit = defineEmits<{
  close: []
  confirm: []
}>()

function handleConfirm() {
  emit('confirm')
}

function handleClose() {
  emit('close')
}
</script>

<template>
  <!-- Backdrop -->
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
    <!-- Modal -->
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
      <!-- Ícone de email -->
      <div class="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-blue-100 rounded-full">
        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
        </svg>
      </div>

      <!-- Título -->
      <h3 class="text-lg font-semibold text-gray-900 text-center mb-2">
        Confirme seu email
      </h3>

      <!-- Mensagem -->
      <p class="text-gray-600 text-center mb-6">
        Enviamos um link de confirmação para:
        <br>
        <strong class="text-gray-900">{{ email }}</strong>
        <br><br>
        Verifique sua caixa de entrada e clique no link para ativar sua conta.
      </p>

      <!-- Botão -->
      <div class="flex justify-center">
        <AppButton @click="handleConfirm" class="px-8">
          Vou confirmar
        </AppButton>
      </div>
    </div>
  </div>
</template>

