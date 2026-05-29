<template>
  <button
    @click="toggleTheme"
    class="p-2 rounded-lg border border-border/50 bg-secondary/50 hover:bg-secondary transition-colors"
    :title="isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro'"
  >
    <!-- Ícone de sol (tema claro) -->
    <svg
      v-if="isDark"
      class="w-5 h-5 text-foreground/70"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
      />
    </svg>
    
    <!-- Ícone de lua (tema escuro) -->
    <svg
      v-else
      class="w-5 h-5 text-foreground/70"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
      />
    </svg>
  </button>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const isDark = ref(true) // Inicia com tema escuro (padrão atual)

const toggleTheme = () => {
  isDark.value = !isDark.value
  
  if (process.client) {
    const html = document.documentElement
    
    if (isDark.value) {
      html.classList.add('dark')
      html.classList.remove('light')
      localStorage.setItem('theme', 'dark')
    } else {
      html.classList.add('light')
      html.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }
}

onMounted(() => {
  if (process.client) {
    // Verifica o tema salvo no localStorage
    const savedTheme = localStorage.getItem('theme')
    const html = document.documentElement
    
    if (savedTheme === 'light') {
      isDark.value = false
      html.classList.add('light')
      html.classList.remove('dark')
    } else {
      isDark.value = true
      html.classList.add('dark')
      html.classList.remove('light')
    }
  }
})
</script>

