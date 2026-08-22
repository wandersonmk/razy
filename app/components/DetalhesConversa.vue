<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { OPCOES_PAUSA, useConversas, type Conversa, type HistoricoEvento } from '~/composables/useConversas'
import { useProfissionais, type Profissional } from '~/composables/useProfissionais'

const props = defineProps<{ conversa: Conversa }>()
const emit = defineEmits<{ close: []; atualizado: [conversa: Conversa] }>()

const { atribuir, arquivar, pausar, despausar, renomearContato, fetchHistorico } = useConversas()
const { profissionais, fetchProfissionais } = useProfissionais()

let toast: any
const carregandoAcao = ref<string | null>(null)
const historico = ref<HistoricoEvento[]>([])
const mostrarPausas = ref(false)
const mostrarAtribuir = ref(false)

const editandoNome = ref(false)
const nomeEmEdicao = ref('')

onMounted(async () => {
  toast = await useToastSafe()
  fetchProfissionais({ silent: true })
  historico.value = await fetchHistorico(props.conversa.id)
})

watch(() => props.conversa.id, async (id) => {
  historico.value = await fetchHistorico(id)
  editandoNome.value = false
})

async function executar(fn: () => Promise<Conversa>, chave: string, msgSucesso: string) {
  carregandoAcao.value = chave
  try {
    const atualizado = await fn()
    emit('atualizado', atualizado)
    toast?.success(msgSucesso)
  } catch (e: any) {
    toast?.error(e?.message || 'Erro ao executar ação')
  } finally {
    carregandoAcao.value = null
    mostrarPausas.value = false
    mostrarAtribuir.value = false
  }
}

const escolherPausa = (minutos: number) => executar(() => pausar(props.conversa.id, minutos), 'pausar', 'Conversa pausada')
const removerPausa = () => executar(() => despausar(props.conversa.id), 'despausar', 'Pausa removida')
const escolherAtribuir = (id: string | null) => executar(() => atribuir(props.conversa.id, id), 'atribuir', id ? 'Conversa atribuída' : 'Atribuição removida')
const alternarArquivar = () => executar(() => arquivar(props.conversa.id, !props.conversa.arquivada), 'arquivar', props.conversa.arquivada ? 'Conversa desarquivada' : 'Conversa arquivada')

function abrirEdicaoNome() {
  nomeEmEdicao.value = props.conversa.nome_contato || ''
  editandoNome.value = true
}

async function salvarNome() {
  const nome = nomeEmEdicao.value.trim()
  if (!nome) { toast?.warning('Informe um nome'); return }
  await executar(() => renomearContato(props.conversa.id, nome), 'nome', 'Nome atualizado')
  editandoNome.value = false
}

const estaPausadoAgora = computed(() => {
  const c = props.conversa
  if (!c.tempo_pausa || !c.tempo_pausa_inicio) return false
  return new Date(c.tempo_pausa_inicio).getTime() + c.tempo_pausa * 1000 > Date.now()
})

function formatarData(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

const rotuloAcao: Record<HistoricoEvento['acao'], string> = {
  atribuido: 'Atribuído',
  desatribuido: 'Desatribuído',
  fechado: 'Fechado'
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-40 bg-black/40 backdrop-blur-[2px] lg:bg-transparent lg:backdrop-blur-0" @click.self="$emit('close')">
      <div class="absolute right-0 top-0 h-full w-full max-w-sm bg-card border-l border-border shadow-2xl overflow-y-auto">
        <!-- Header -->
        <div class="relative p-5 bg-gradient-to-br from-primary/15 via-primary/5 to-transparent border-b border-border">
          <button @click="$emit('close')" class="absolute right-4 top-4 text-muted-foreground hover:text-foreground transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
          <AvatarContato :nome="conversa.nome_contato" :numero="conversa.numero" :photo="conversa.photo" size-class="w-16 h-16 text-xl mb-3" />

          <!-- Nome do contato (editável) -->
          <div v-if="!editandoNome" class="flex items-center gap-1.5 group">
            <p class="font-semibold text-foreground text-lg">{{ conversa.nome_contato || conversa.numero }}</p>
            <button @click="abrirEdicaoNome" class="text-muted-foreground hover:text-primary transition shrink-0" title="Editar nome">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
            </button>
          </div>
          <div v-else class="flex items-center gap-1.5">
            <input
              v-model="nomeEmEdicao"
              type="text"
              autofocus
              @keyup.enter="salvarNome"
              @keyup.esc="editandoNome = false"
              class="flex-1 px-2 py-1 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <button @click="salvarNome" :disabled="carregandoAcao === 'nome'" class="p-1.5 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition disabled:opacity-50">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            </button>
            <button @click="editandoNome = false" class="p-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <p class="text-sm text-muted-foreground">{{ conversa.numero }}</p>
          <p class="text-xs text-muted-foreground mt-1">Canal: {{ conversa.instancia?.nome_instancia || 'removido' }}</p>
        </div>

        <div class="p-5 space-y-5">
          <!-- Atribuição -->
          <div>
            <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Atribuído a</p>
            <div class="relative">
              <button @click="mostrarAtribuir = !mostrarAtribuir" class="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground hover:border-primary/40 transition">
                <span>{{ conversa.profissional?.nome || 'Ninguém' }}</span>
                <svg class="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
              </button>
              <div v-if="mostrarAtribuir" class="absolute z-10 mt-1 w-full bg-card border border-border rounded-lg shadow-lg overflow-hidden">
                <button
                  v-if="conversa.assigned_to_professional_id"
                  @click="escolherAtribuir(null)"
                  class="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:bg-muted transition"
                >Remover atribuição</button>
                <button
                  v-for="p in profissionais"
                  :key="p.id"
                  @click="escolherAtribuir(p.id)"
                  class="w-full text-left px-3 py-2 text-sm text-foreground hover:bg-muted transition"
                  :class="p.id === conversa.assigned_to_professional_id ? 'bg-primary/10 text-primary font-medium' : ''"
                >{{ p.nome }}</button>
              </div>
            </div>
          </div>

          <!-- Ações -->
          <div class="space-y-2">
            <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Ações</p>

            <div class="relative">
              <button
                @click="mostrarPausas = !mostrarPausas"
                :disabled="carregandoAcao === 'pausar'"
                class="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 text-amber-700 dark:text-amber-400 text-sm font-medium hover:bg-amber-500/20 transition disabled:opacity-50"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                {{ estaPausadoAgora ? 'Ajustar pausa' : 'Pausar' }}
              </button>
              <div v-if="mostrarPausas" class="absolute z-10 mt-1 w-full bg-card border border-border rounded-lg shadow-lg overflow-hidden">
                <button
                  v-for="op in OPCOES_PAUSA"
                  :key="op.minutos"
                  @click="escolherPausa(op.minutos)"
                  class="w-full text-left px-3 py-2 text-sm text-foreground hover:bg-muted transition"
                >{{ op.label }}</button>
                <button v-if="estaPausadoAgora" @click="removerPausa" class="w-full text-left px-3 py-2 text-sm text-red-500 hover:bg-muted transition border-t border-border">
                  Remover pausa
                </button>
              </div>
            </div>

            <button
              @click="alternarArquivar"
              :disabled="carregandoAcao === 'arquivar'"
              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition disabled:opacity-50"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 01-2-2V4a2 2 0 012-2h14a2 2 0 012 2v2a2 2 0 01-2 2M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>
              {{ conversa.arquivada ? 'Desarquivar' : 'Arquivar' }}
            </button>
          </div>

          <!-- Histórico -->
          <div>
            <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Histórico</p>
            <div v-if="!historico.length" class="text-xs text-muted-foreground">Nenhum evento ainda.</div>
            <ul v-else class="space-y-2">
              <li v-for="h in historico" :key="h.id" class="text-xs flex items-start gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-primary/60 mt-1.5 shrink-0" />
                <span class="text-foreground">
                  <strong>{{ rotuloAcao[h.acao] }}</strong>
                  <span v-if="h.profissional_nome_snapshot"> — {{ h.profissional_nome_snapshot }}</span>
                  <span class="text-muted-foreground"> · {{ formatarData(h.created_at) }}</span>
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
