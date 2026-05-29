<script setup lang="ts">
import { ref, computed } from 'vue'

const email = ref('')
const password = ref('')
let toast: any
onMounted(async () => {
  toast = await useToastSafe()
})

const { signInWithEmailAndPassword, isLoading, errorMessage } = process.client ? useAuth() : {
  signInWithEmailAndPassword: async () => {},
  isLoading: ref(false),
  errorMessage: ref(null)
}

// Validações em tempo real
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const isEmailValid = computed(() => {
  if (!email.value) return true // Não mostra erro se estiver vazio
  return emailRegex.test(email.value)
})

const emailError = computed(() => {
  if (!email.value || isEmailValid.value) return ''
  return 'Email inválido'
})

async function handleLogin() {
  if (!email.value || !password.value) {
    toast?.warning('Preencha todos os campos')
    return
  }
  
  // Validação de email
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email.value)) {
    toast?.error('Digite um email válido')
    return
  }
  
  try {
    console.log('LoginForm: Iniciando login...')
    const result = await signInWithEmailAndPassword(email.value, password.value)
    await new Promise(resolve => setTimeout(resolve, 200))

    // Se login falhou, mostra erro
    if (!result) {
      console.error('LoginForm: Erro no login:', errorMessage.value)
      toast?.error(errorMessage.value || 'Erro ao efetuar login. Verifique seus dados.')
      return
    }

    // Se login OK, mostra sucesso
    const { isAuthenticated, user } = useAuth()
    console.log('LoginForm: Estado atual após delay:', { 
      isAuthenticated: isAuthenticated.value, 
      hasUser: !!user.value,
      email: user.value?.email 
    })

    if (process.client && user.value?.email) {
      localStorage.setItem('user_email', user.value.email)
      console.log('LoginForm: Email salvo no localStorage:', user.value.email)
    }

    toast?.success('Login realizado com sucesso!')
    await navigateTo('/')
    console.log('LoginForm: NavigateTo executado')
  } catch (error) {
    console.error('LoginForm: Erro inesperado no login:', error)
    toast?.error('Erro inesperado ao efetuar login.')
  }
}
</script>

<template>
  <div class="w-full max-w-sm">
    <!-- Card principal -->
    <div class="rounded-xl border border-border/50 bg-secondary p-6 shadow-lg backdrop-blur-sm">
    <div class="space-y-1">
      <h2 class="text-lg font-semibold">Faça login na plataforma</h2>
      <p class="text-sm text-muted-foreground">Acesse sua conta com email e senha</p>
    </div>

    <form @submit.prevent="handleLogin" class="mt-6 space-y-3">
      <div>
        <AppInput
          v-model="email"
          type="email"
          placeholder="Email"
          autocomplete="email"
          required
          :invalid="!!emailError"
          :valid="!!email && isEmailValid"
        />
        <div v-if="emailError" class="text-xs text-red-500 mt-1 px-1">
          {{ emailError }}
        </div>
      </div>
      
      <AppInput
        v-model="password"
        type="password"
        placeholder="Senha"
        autocomplete="current-password"
        required
        :valid="!!password"
      />
      
      <div class="text-right">
        <NuxtLink 
          to="/recuperar-senha" 
          class="text-xs text-foreground/55 hover:text-foreground transition-colors"
        >
          Recuperar senha
        </NuxtLink>
      </div>
      
      <AppButton 
        type="submit" 
        block 
        :disabled="isLoading || !email || !password || !isEmailValid"
      >
        <span v-if="isLoading">Entrando...</span>
        <span v-else>Entrar</span>
      </AppButton>
    </form>
    </div>
  </div>
</template>





