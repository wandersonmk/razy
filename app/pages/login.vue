<script setup lang="ts">
// Middleware para redirecionar usuários já logados
definePageMeta({
  middleware: 'guest',
  layout: 'auth'
})
</script>

<template>
  <div class="min-h-[calc(100vh-0px)] w-full flex items-center justify-center p-4">
    <AuthTabs />
  </div>
</template>


