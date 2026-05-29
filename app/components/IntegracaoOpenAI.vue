<template>
  <div class="rounded-xl border border-border bg-card p-6 space-y-4">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center shrink-0">
        <svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
          <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.843-3.369 2.02-1.168a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.402-.681zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"/>
        </svg>
      </div>
      <div class="flex-1">
        <p class="text-sm font-semibold text-foreground">OpenAI</p>
        <p class="text-xs text-muted-foreground">Chave de API para geração de mensagens com IA</p>
      </div>
      <span v-if="temChave" class="inline-flex items-center gap-1.5 text-xs font-medium text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-2.5 py-1 rounded-full">
        <span class="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0"/>
        Configurada
      </span>
      <span v-else class="inline-flex items-center gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-2.5 py-1 rounded-full">
        <span class="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0"/>
        Não configurada
      </span>
    </div>

    <!-- Info -->
    <div class="text-xs text-muted-foreground bg-muted/30 rounded-lg p-3 space-y-1">
      <p>• A chave é salva de forma segura no banco de dados, vinculada à sua conta.</p>
      <p>• Somente o servidor de IA consegue ler esta chave — nunca é exposta ao navegador.</p>
      <p>• Se não configurada, o servidor usa a chave padrão do sistema como fallback.</p>
    </div>

    <!-- Campo -->
    <div>
      <label class="block text-sm font-medium text-foreground mb-1.5">
        Chave da API <span class="text-muted-foreground font-normal">(sk-...)</span>
      </label>
      <!-- Chave atual mascarada (só visual, nunca é o valor real) -->
      <div v-if="temChave && !editando" class="flex items-center gap-2 mb-2">
        <div class="flex-1 px-3 py-2 rounded-lg border border-border bg-muted/30 text-sm font-mono text-muted-foreground tracking-wider">
          {{ chaveMascarada || 'sk-proj-••••••••••••••••••••••' }}
        </div>
        <button
          @click="editando = true"
          class="px-4 py-2 text-sm font-medium border border-border rounded-lg text-foreground hover:bg-muted transition shrink-0"
        >
          Trocar chave
        </button>
      </div>
      <div v-if="!temChave || editando" class="flex gap-2">
        <div class="relative flex-1">
          <input
            v-model="chaveInput"
            :type="mostrarChave ? 'text' : 'password'"
            placeholder="sk-proj-..."
            autocomplete="off"
            class="w-full px-3 py-2 pr-10 rounded-lg border border-border bg-background text-foreground text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          <button
            type="button"
            @click="mostrarChave = !mostrarChave"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition"
          >
            <svg v-if="mostrarChave" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
          </button>
        </div>
        <button
          @click="salvar"
          :disabled="salvando || !chaveInput.trim()"
          class="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50 shrink-0"
        >
          {{ salvando ? 'Salvando...' : 'Salvar' }}
        </button>
        <button
          v-if="editando"
          @click="editando = false; chaveInput = ''"
          class="px-3 py-2 text-sm border border-border rounded-lg text-muted-foreground hover:bg-muted transition shrink-0"
        >
          Cancelar
        </button>
      </div>
      <p v-if="erro" class="text-xs text-red-500 mt-1.5">{{ erro }}</p>
      <p v-if="sucesso" class="text-xs text-green-600 dark:text-green-400 mt-1.5">✓ Chave salva com sucesso!</p>
    </div>

    <!-- Remover -->
    <div v-if="temChave" class="flex items-center justify-between pt-3 border-t border-border">
      <p class="text-xs text-muted-foreground">Remover a chave e usar a chave padrão do sistema</p>
      <button
        @click="remover"
        :disabled="removendo"
        class="text-xs text-red-500 hover:text-red-600 hover:underline transition disabled:opacity-50"
      >
        {{ removendo ? 'Removendo...' : 'Remover chave' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

let _supabase: any = null
function getSupabase() {
  if (!_supabase && typeof window !== 'undefined') _supabase = useSupabaseClient()
  return _supabase
}

const temChave = ref(false)
const chaveMascarada = ref<string | null>(null)
const editando = ref(false)
const chaveInput = ref('')
const mostrarChave = ref(false)
const salvando = ref(false)
const removendo = ref(false)
const erro = ref('')
const sucesso = ref(false)

onMounted(async () => {
  try {
    const sb = getSupabase()
    if (!sb) return
    const { data: { user } } = await sb.auth.getUser()
    if (!user) return
    // Busca via server route — retorna apenas a versão mascarada, nunca a chave real
    const data = await $fetch<{ configurada: boolean; chave_mascarada: string | null }>('/api/integracoes/openai')
    temChave.value = data.configurada
    chaveMascarada.value = data.chave_mascarada
  } catch { /* silencia */ }
})

async function salvar() {
  const sb = getSupabase()
  if (!sb || !chaveInput.value.trim()) return
  salvando.value = true
  erro.value = ''
  sucesso.value = false
  try {
    const { data: { user } } = await sb.auth.getUser()
    if (!user) throw new Error('Sessão expirada')
    const { error: err } = await sb
      .from('integracoes')
      .upsert(
        { usuario_id: user.id, openai_api_key: chaveInput.value.trim(), updated_at: new Date().toISOString() },
        { onConflict: 'usuario_id' }
      )
    if (err) throw err
    // Mascara antes de limpar o input
    const nova = chaveInput.value.trim()
    if (nova.length > 8) chaveMascarada.value = `${nova.slice(0, 12)}...${nova.slice(-4)}`
    temChave.value = true
    editando.value = false
    chaveInput.value = ''
    sucesso.value = true
    setTimeout(() => { sucesso.value = false }, 3000)
  } catch (e: any) {
    erro.value = e.message || 'Erro ao salvar chave'
  } finally {
    salvando.value = false
  }
}

async function remover() {
  const sb = getSupabase()
  if (!sb) return
  removendo.value = true
  try {
    const { data: { user } } = await sb.auth.getUser()
    if (!user) return
    await sb
      .from('integracoes')
      .update({ openai_api_key: null, updated_at: new Date().toISOString() })
      .eq('usuario_id', user.id)
    temChave.value = false
  } finally {
    removendo.value = false
  }
}
</script>
