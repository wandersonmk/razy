<template>
  <div class="flex flex-col items-center justify-center py-8 px-4">
    <div class="bg-dark-800 rounded-lg shadow-lg p-8 w-full max-w-md text-center">
      <h2 class="text-2xl font-bold mb-4">Verifique seu e-mail</h2>
      <p class="mb-6 text-gray-300">
        Enviamos um link de redefinição de senha para o seu e-mail.<br>
        Acesse sua caixa de entrada e siga as instruções para criar uma nova senha.
      </p>
      <button @click="irParaLogin" class="w-full py-2 px-4 rounded bg-purple-500 hover:bg-purple-600 text-white font-semibold transition">
        Acessar e-mail e voltar para login
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
function irParaLogin() {
  router.push('/login')
}
</script>

<style scoped>
.bg-dark-800 {
  background: #18181b;
}
</style>

