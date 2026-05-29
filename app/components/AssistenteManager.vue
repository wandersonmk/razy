<template>
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Header -->
    <div class="flex items-center justify-between p-6 border-b border-border">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
        </div>
        <div>
          <h2 class="text-lg font-semibold text-foreground">Assistente de Atendimento</h2>
          <p class="text-sm text-muted-foreground">IA que atende o cliente quando ele responde e encaminha ao atendente</p>
        </div>
      </div>
      <!-- Toggle ativo -->
      <div class="flex items-center gap-2">
        <span class="text-sm text-muted-foreground">{{ form.ativo ? 'Ativo' : 'Inativo' }}</span>
        <button
          type="button"
          @click="form.ativo = !form.ativo"
          :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none', form.ativo ? 'bg-primary' : 'bg-muted']"
        >
          <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.ativo ? 'translate-x-5' : 'translate-x-0']"/>
        </button>
      </div>
    </div>

    <div class="p-6 space-y-5">
      <!-- Como funciona -->
      <div class="flex items-start gap-2 text-xs p-3 rounded-lg bg-primary/5 border border-primary/20 text-foreground">
        <svg class="w-4 h-4 shrink-0 mt-0.5 text-primary" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
        <span>
          Quando o cliente responde a um disparo (texto ou <strong>áudio</strong>, que é transcrito automaticamente), o assistente
          atende usando as informações abaixo, coleta os dados e — quando a coleta termina — envia um resumo para o número do atendente.
          O contexto da conversa é mantido pelo número que recebeu a mensagem.
        </span>
      </div>

      <!-- Nome da empresa -->
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Nome da empresa</label>
        <input v-model="form.empresa_nome" type="text" placeholder="Ex: Razy Corretora"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
      </div>

      <!-- Informações da empresa -->
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Informações da empresa e dos planos</label>
        <textarea v-model="form.empresa_info" rows="5"
          placeholder="Descreva os produtos/planos, preços, diferenciais, coberturas, condições... A IA usa isso para responder o cliente."
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
      </div>

      <!-- Horário de funcionamento -->
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Horário de funcionamento</label>
        <input v-model="form.horario_funcionamento" type="text" placeholder="Ex: Seg a Sex, 8h às 18h"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
      </div>

      <!-- Instrução do assistente -->
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Instruções do assistente</label>
        <textarea v-model="form.instrucao" rows="5"
          placeholder="Como o assistente deve se comportar: tom de voz, o que perguntar ao cliente, quais dados coletar, quando encaminhar ao atendente..."
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
        <p class="text-xs text-muted-foreground mt-1">Ex: "Pergunte o nome, a cidade e o tipo de plano de interesse. Seja cordial. Quando tiver esses dados, encaminhe ao atendente."</p>
      </div>

      <!-- Telefone do atendente -->
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">Número do atendente (handoff)</label>
        <input v-model="form.atendente_telefone" type="text" placeholder="Ex: 5511999998888"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
        <p class="text-xs text-muted-foreground mt-1">Quando a coleta de dados terminar, o assistente envia o resumo do atendimento para este número via WhatsApp.</p>
      </div>

      <!-- Ações -->
      <div class="flex items-center justify-between pt-2 border-t border-border">
        <p v-if="sucesso" class="text-xs text-green-600 dark:text-green-400">✓ Configurações salvas!</p>
        <p v-else-if="erro" class="text-xs text-red-500">{{ erro }}</p>
        <span v-else class="text-xs text-muted-foreground"></span>
        <button
          @click="salvar"
          :disabled="salvando"
          class="px-5 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50"
        >
          {{ salvando ? 'Salvando...' : 'Salvar configurações' }}
        </button>
      </div>
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

const form = ref({
  ativo: true,
  empresa_nome: '',
  empresa_info: '',
  horario_funcionamento: '',
  instrucao: '',
  atendente_telefone: ''
})

const salvando = ref(false)
const sucesso = ref(false)
const erro = ref('')

onMounted(async () => {
  const sb = getSupabase()
  if (!sb) return
  try {
    const { data: { user } } = await sb.auth.getUser()
    if (!user) return
    const { data } = await sb
      .from('assistentes')
      .select('ativo, empresa_nome, empresa_info, horario_funcionamento, instrucao, atendente_telefone')
      .eq('usuario_id', user.id)
      .maybeSingle()
    if (data) {
      form.value = {
        ativo: data.ativo ?? true,
        empresa_nome: data.empresa_nome || '',
        empresa_info: data.empresa_info || '',
        horario_funcionamento: data.horario_funcionamento || '',
        instrucao: data.instrucao || '',
        atendente_telefone: data.atendente_telefone || ''
      }
    }
  } catch { /* silencia */ }
})

async function salvar() {
  const sb = getSupabase()
  if (!sb) return
  salvando.value = true
  erro.value = ''
  sucesso.value = false
  try {
    const { data: { user } } = await sb.auth.getUser()
    if (!user) throw new Error('Sessão expirada')
    const { error: err } = await sb
      .from('assistentes')
      .upsert(
        { usuario_id: user.id, ...form.value, updated_at: new Date().toISOString() },
        { onConflict: 'usuario_id' }
      )
    if (err) throw err
    sucesso.value = true
    setTimeout(() => { sucesso.value = false }, 3000)
  } catch (e: any) {
    erro.value = e.message || 'Erro ao salvar'
  } finally {
    salvando.value = false
  }
}
</script>
