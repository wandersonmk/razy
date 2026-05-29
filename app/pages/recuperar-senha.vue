<template>
  <div class="min-h-[calc(100vh-0px)] w-full flex items-center justify-center p-4">
    <div class="w-full max-w-sm mx-auto">
      <div v-if="!showModal">
        <!-- Card principal -->
        <div class="rounded-xl border border-border/50 bg-secondary p-6 shadow-lg backdrop-blur-sm">
          <div class="space-y-1">
            <h2 class="text-lg font-medium text-foreground/85">Recuperar senha</h2>
            <p class="text-sm text-foreground/60">Digite seu email para receber as instruções de recuperação</p>
          </div>
          <form @submit.prevent="handleSubmit" class="mt-6 space-y-3">
            <div>
              <AppInput
                v-model="email"
                type="email"
                placeholder="Digite seu email"
                autocomplete="email"
                required
                :valid="!!email && isEmailValid"
              />
              <div v-if="emailError" class="text-xs text-red-500 mt-1 px-1">
                {{ emailError }}
              </div>
            </div>
            <AppButton 
              type="submit" 
              block 
              :disabled="isLoading || !email || !isEmailValid"
            >
              <span v-if="isLoading">Enviando...</span>
              <span v-else>Enviar instruções</span>
            </AppButton>
          </form>
          <div class="mt-4 text-center">
            <NuxtLink 
              to="/login" 
              class="text-sm text-foreground/60 hover:text-foreground transition-colors"
            >
              Voltar para o login
            </NuxtLink>
          </div>
        </div>
      </div>
      <div v-else>
        <EmailCheckModal />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import EmailCheckModal from '~/components/EmailCheckModal.vue'

definePageMeta({
  layout: 'auth',
  middleware: 'guest'
})

const email = ref('')
const isLoading = ref(false)
const showModal = ref(false)
const router = useRouter()

// Validações em tempo real
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const isEmailValid = computed(() => {
  return email.value.length === 0 || emailRegex.test(email.value)
})

const emailError = computed(() => {
  if (email.value.length > 0 && !emailRegex.test(email.value)) {
    return 'Digite um email válido'
  }
  return null
})

const handleSubmit = async () => {
  if (!isEmailValid.value) return
  isLoading.value = true
  try {
    const res = await fetch('https://kxvraxkisrgyhntifxrc.supabase.co/auth/v1/recover', {
      method: 'POST',
      headers: {
        'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4dnJheGtpc3JneWhudGlmeHJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYzODc5MDUsImV4cCI6MjA3MTk2MzkwNX0.tOV1n6ogyk9wuU_M4eBPhe5LUttuIWpXZQPkk2Ctc5U',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email: email.value })
    })
    if (res.ok) {
      showModal.value = true
    } else {
      const data = await res.json()
      alert(data?.msg || 'Erro ao enviar instruções. Tente novamente.')
    }
  } catch (err) {
    alert('Erro ao conectar ao serviço. Tente novamente.')
  } finally {
    isLoading.value = false
  }
}
</script>
