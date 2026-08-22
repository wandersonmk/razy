<template>
  <div class="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
    <!-- Header -->
    <div class="flex items-center justify-between p-6 border-b border-border gap-3">
      <div class="flex items-center gap-3 min-w-0">
        <button type="button" @click="$emit('voltar')"
          class="p-2 -ml-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition shrink-0" title="Voltar">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
        </button>
        <div class="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center shrink-0">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
        </div>
        <div class="min-w-0">
          <h2 class="text-lg font-semibold text-foreground truncate">IA de {{ nomeProfissional }}</h2>
          <p class="text-sm text-muted-foreground">Configuração própria, separada do assistente principal</p>
        </div>
      </div>
      <!-- Toggle ativo -->
      <div class="flex items-center gap-2 shrink-0">
        <span class="text-sm text-muted-foreground">{{ form.ativo ? 'Ligada' : 'Desligada' }}</span>
        <button type="button" @click="form.ativo = !form.ativo"
          :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none', form.ativo ? 'bg-emerald-500' : 'bg-muted']">
          <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.ativo ? 'translate-x-5' : 'translate-x-0']"/>
        </button>
      </div>
    </div>

    <div v-if="carregando" class="p-10 text-center text-sm text-muted-foreground">Carregando...</div>

    <template v-else>
      <div v-if="!form.ativo" class="mx-6 mt-5 flex items-start gap-2 text-xs p-3 rounded-lg bg-muted/40 border border-border text-muted-foreground">
        <svg class="w-4 h-4 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
        <span>Desligada é o comportamento padrão: {{ nomeProfissional }} continua respondendo pelo próprio celular, o painel só acompanha. Ligue acima só se quiser que a IA responda automaticamente por ele.</span>
      </div>

      <!-- Aba única: configuração -->
      <div class="p-6 space-y-5">
        <div>
          <label class="block text-sm font-medium text-foreground mb-1">Nome da empresa</label>
          <input v-model="form.empresa_nome" type="text" placeholder="Ex: Razy Corretora"
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground mb-1">Informações da empresa</label>
          <textarea v-model="form.empresa_info" rows="4"
            placeholder="O que essa IA precisa saber para responder pelo cliente."
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground mb-1">Horário de funcionamento</label>
          <input v-model="form.horario_funcionamento" type="text" placeholder="Ex: Seg a Sex, 8h às 18h"
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground mb-1">Instruções</label>
          <textarea v-model="form.instrucao" rows="6"
            placeholder="Como essa IA deve se comportar ao responder no lugar do profissional: tom de voz, o que perguntar, quando avisar que é uma IA..."
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
        </div>

        <!-- Capacidades -->
        <div class="rounded-xl border border-border overflow-hidden">
          <div class="flex items-center gap-3 p-4">
            <div class="w-9 h-9 shrink-0 rounded-lg bg-violet-500/10 flex items-center justify-center">
              <svg class="text-violet-500" style="width:1.125rem;height:1.125rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-foreground">Ler imagens</p>
              <p class="text-xs text-muted-foreground mt-0.5">Descreve fotos e comprovantes enviados pelo cliente.</p>
            </div>
            <button type="button" @click="form.ler_imagem = !form.ler_imagem"
              :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors', form.ler_imagem ? 'bg-violet-500' : 'bg-muted']">
              <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.ler_imagem ? 'translate-x-5' : 'translate-x-0']"/>
            </button>
          </div>
          <div v-if="form.ler_imagem" class="px-4 pb-4 border-t border-border pt-3">
            <textarea v-model="form.instrucao_imagem" rows="3" placeholder="Instrução customizada (opcional)"
              class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
          </div>
        </div>

        <div class="rounded-xl border border-border overflow-hidden">
          <div class="flex items-center gap-3 p-4">
            <div class="w-9 h-9 shrink-0 rounded-lg bg-amber-500/10 flex items-center justify-center">
              <svg class="text-amber-500" style="width:1.125rem;height:1.125rem" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-foreground">Ler documentos</p>
              <p class="text-xs text-muted-foreground mt-0.5">Extrai o conteúdo de PDF/Word/txt enviados pelo cliente.</p>
            </div>
            <button type="button" @click="form.ler_documento = !form.ler_documento"
              :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors', form.ler_documento ? 'bg-amber-500' : 'bg-muted']">
              <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.ler_documento ? 'translate-x-5' : 'translate-x-0']"/>
            </button>
          </div>
          <div v-if="form.ler_documento" class="px-4 pb-4 border-t border-border pt-3">
            <textarea v-model="form.instrucao_documento" rows="3" placeholder="Instrução customizada (opcional)"
              class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"/>
          </div>
        </div>

        <!-- Pausa -->
        <div class="rounded-xl border border-border p-4 space-y-3">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-medium text-foreground">Pausar quando {{ nomeProfissional }} responder pelo celular</p>
              <p class="text-xs text-muted-foreground mt-0.5">Se ele mandar uma mensagem manualmente, esta IA para de responder aquele contato por um tempo.</p>
            </div>
            <button type="button" @click="form.pausa_ativa = !form.pausa_ativa"
              :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors', form.pausa_ativa ? 'bg-primary' : 'bg-muted']">
              <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', form.pausa_ativa ? 'translate-x-5' : 'translate-x-0']"/>
            </button>
          </div>
          <div v-if="form.pausa_ativa" class="pt-1">
            <div class="flex items-center gap-2">
              <input v-model.number="form.pausa_minutos" type="number" min="1"
                class="w-28 px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"/>
              <span class="text-sm text-muted-foreground">minutos sem responder após ele assumir</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Ações -->
      <div class="flex items-center justify-between gap-3 p-6 border-t border-border">
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProfissionais, type Profissional } from '~/composables/useProfissionais'
import { useAssistentesProfissionais } from '~/composables/useAssistentesProfissionais'

const props = defineProps<{ profissionalId: string }>()
const emit = defineEmits<{ voltar: []; salvo: [] }>()

const { profissionais, fetchProfissionais } = useProfissionais()
const { buscarPorProfissional, salvar: salvarConfig } = useAssistentesProfissionais()

let toast: any
const carregando = ref(true)
const salvando = ref(false)
const sucesso = ref(false)
const erro = ref('')

const profissional = ref<Profissional | null>(null)
const nomeProfissional = computed(() => profissional.value?.nome || 'profissional')

const form = ref({
  ativo: false,
  empresa_nome: '',
  empresa_info: '',
  horario_funcionamento: '',
  instrucao: '',
  ler_imagem: false,
  instrucao_imagem: '',
  ler_documento: false,
  instrucao_documento: '',
  pausa_ativa: true,
  pausa_minutos: 30
})

function aplicar(data: any) {
  form.value = {
    ativo: data?.ativo ?? false,
    empresa_nome: data?.empresa_nome || '',
    empresa_info: data?.empresa_info || '',
    horario_funcionamento: data?.horario_funcionamento || '',
    instrucao: data?.instrucao || '',
    ler_imagem: data?.ler_imagem ?? false,
    instrucao_imagem: data?.instrucao_imagem || '',
    ler_documento: data?.ler_documento ?? false,
    instrucao_documento: data?.instrucao_documento || '',
    pausa_ativa: data?.pausa_ativa ?? true,
    pausa_minutos: data?.pausa_minutos ?? 30
  }
}

onMounted(async () => {
  toast = await useToastSafe()
  carregando.value = true
  try {
    await fetchProfissionais({ silent: true })
    profissional.value = profissionais.value.find((p) => p.id === props.profissionalId) || null
    const existente = await buscarPorProfissional(props.profissionalId)
    aplicar(existente)
  } finally {
    carregando.value = false
  }
})

async function salvar() {
  salvando.value = true
  erro.value = ''
  sucesso.value = false
  try {
    await salvarConfig(props.profissionalId, {
      ativo: form.value.ativo,
      empresa_nome: form.value.empresa_nome,
      empresa_info: form.value.empresa_info,
      horario_funcionamento: form.value.horario_funcionamento,
      instrucao: form.value.instrucao,
      ler_imagem: form.value.ler_imagem,
      instrucao_imagem: form.value.instrucao_imagem.trim() || null,
      ler_documento: form.value.ler_documento,
      instrucao_documento: form.value.instrucao_documento.trim() || null,
      pausa_ativa: form.value.pausa_ativa,
      pausa_minutos: form.value.pausa_minutos
    })
    sucesso.value = true
    toast?.success(`IA de ${nomeProfissional.value} salva!`)
    emit('salvo')
    setTimeout(() => { sucesso.value = false }, 3000)
  } catch (e: any) {
    erro.value = e.message || 'Erro ao salvar'
    toast?.error(erro.value)
  } finally {
    salvando.value = false
  }
}
</script>
