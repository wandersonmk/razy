<template>
  <div class="min-h-[calc(100vh-0px)] w-full flex items-center justify-center p-4">
    <RedefinirSenhaForm />
  </div>
</template>

<script setup lang="ts">
import RedefinirSenhaForm from '../components/RedefinirSenhaForm.vue'

definePageMeta({
  layout: 'auth',
  middleware: 'guest'
})
</script>
