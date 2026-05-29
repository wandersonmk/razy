<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref<'login' | 'register'>('login')

function setActiveTab(tab: 'login' | 'register') {
  activeTab.value = tab
}
</script>

<template>
  <div class="w-full max-w-sm mx-auto">
    <!-- Navegação das abas -->
    <div class="flex bg-muted rounded-lg p-1 mb-6">
      <button
        @click="setActiveTab('login')"
        :class="[
          'flex-1 py-2 px-4 text-sm font-medium rounded-md transition-all duration-200',
          activeTab === 'login'
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
        ]"
      >
        Entrar
      </button>
      
      <button
        @click="setActiveTab('register')"
        :class="[
          'flex-1 py-2 px-4 text-sm font-medium rounded-md transition-all duration-200',
          activeTab === 'register'
            ? 'bg-primary text-primary-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
        ]"
      >
        Cadastrar
      </button>
    </div>

    <!-- Conteúdo das abas -->
    <div class="tab-content">
      <Transition
        name="fade"
        mode="out-in"
      >
        <LoginForm v-if="activeTab === 'login'" key="login" />
        <RegisterForm v-else-if="activeTab === 'register'" key="register" />
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

