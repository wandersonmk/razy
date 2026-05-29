<template>
  <div class="w-full max-w-sm mx-auto">
    <div class="rounded-xl border border-border/50 bg-secondary p-6 shadow-lg backdrop-blur-sm">
      <div class="space-y-1 mb-4">
        <h2 class="text-lg font-medium text-foreground/85">Redefinir senha</h2>
        <p class="text-sm text-foreground/60">Digite sua nova senha abaixo</p>
      </div>
      <form @submit.prevent="handleSubmit" class="space-y-3">
        <AppInput
          v-model="password"
          type="password"
          placeholder="Nova senha"
          autocomplete="new-password"
          required
          :valid="!!password && password.length >= 6"
        />
        <AppInput
          v-model="confirmPassword"
          type="password"
          placeholder="Confirmar nova senha"
          autocomplete="new-password"
          required
          :valid="!!confirmPassword && confirmPassword === password"
        />
        <div v-if="error" class="text-xs text-red-500 mt-1 px-1">{{ error }}</div>
        <AppButton type="submit" block :disabled="isLoading || !isFormValid">
          <span v-if="isLoading">Salvando...</span>
          <span v-else>Salvar nova senha</span>
        </AppButton>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToastSafe } from '~/composables/useToastSafe'

const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const isLoading = ref(false)
const route = useRoute()
const router = useRouter()

const isFormValid = computed(() => {
  return password.value.length >= 6 && confirmPassword.value === password.value
})

async function handleSubmit() {
  error.value = ''
  if (!isFormValid.value) {
    error.value = 'Preencha corretamente os campos.'
    return
  }
  isLoading.value = true
  try {
    // Token de redefinição de senha (do Supabase)
    let accessToken = route.query.access_token as string | undefined
    // Se não veio na query, tenta pegar do hash
    if (!accessToken && window && window.location.hash) {
      const hash = window.location.hash.substring(1) // remove o #
      const params = new URLSearchParams(hash)
      accessToken = params.get('access_token') || undefined
    }
    if (!accessToken) {
      error.value = 'Token de redefinição inválido.'
      isLoading.value = false
      return
    }
    // Chamada para redefinir senha via Supabase (PUT /auth/v1/user)
    const res = await fetch('https://kxvraxkisrgyhntifxrc.supabase.co/auth/v1/user', {
      method: 'PUT',
      headers: {
        'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4dnJheGtpc3JneWhudGlmeHJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYzODc5MDUsImV4cCI6MjA3MTk2MzkwNX0.tOV1n6ogyk9wuU_M4eBPhe5LUttuIWpXZQPkk2Ctc5U',
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        password: password.value
      })
    })
    if (res.ok) {
      // Toast de sucesso
      const toast = await useToastSafe()
      if (toast) {
        toast.success('Senha alterada com sucesso!')
      } else {
        alert('Senha alterada com sucesso!')
      }
      // Redireciona imediatamente para login
      router.push('/login')
    } else {
      const data = await res.json()
      error.value = data?.msg || 'Erro ao redefinir senha. Tente novamente.'
    }
  } catch (err) {
    error.value = 'Erro ao conectar ao serviço. Tente novamente.'
  } finally {
    isLoading.value = false
  }
}
</script>

