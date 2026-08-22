<template>
  <div>
    <div class="bg-card border border-border rounded-2xl overflow-hidden mb-6">
      <div class="p-6 pb-5">
        <h2 class="text-lg font-bold text-foreground">IA dos Profissionais</h2>
        <p class="text-sm text-muted-foreground mt-0.5">
          Modelo separado do assistente principal — liga/desliga a IA de cada profissional, com a própria configuração. Desligada é o padrão: o profissional responde pelo celular dele.
        </p>
      </div>
      <div class="h-1.5 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500" />
    </div>

    <div v-if="isLoading" class="grid gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="i in 3" :key="i" class="h-24 bg-muted/30 rounded-xl animate-pulse" />
    </div>

    <div v-else-if="!profissionais.length" class="text-center py-16 bg-card border border-border rounded-2xl">
      <p class="text-foreground font-medium">Nenhum profissional cadastrado ainda</p>
      <p class="text-sm text-muted-foreground mt-1">
        Cadastre um profissional em <NuxtLink to="/profissionais" class="text-primary hover:underline">Profissionais &amp; Canais</NuxtLink> — a IA dele aparece aqui automaticamente.
      </p>
    </div>

    <div v-else class="grid gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="p in profissionais"
        :key="p.id"
        class="p-4 bg-card border border-border rounded-xl hover:border-primary/40 transition"
      >
        <div class="flex items-start gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shrink-0 text-white font-semibold text-xs">
            {{ iniciais(p.nome) }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-foreground truncate">{{ p.nome }}</p>
            <p class="text-xs text-muted-foreground truncate">{{ p.instancia?.nome_instancia || 'Sem canal conectado' }}</p>
          </div>
          <button
            type="button"
            @click="alternar(p)"
            :disabled="ligando === p.id"
            :class="['relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors disabled:opacity-50', iaDoProfissionalAtiva(p) ? 'bg-emerald-500' : 'bg-muted']"
          >
            <span :class="['pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform', iaDoProfissionalAtiva(p) ? 'translate-x-5' : 'translate-x-0']"/>
          </button>
        </div>
        <div class="flex items-center justify-between mt-3">
          <span class="text-xs" :class="iaDoProfissionalAtiva(p) ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'">
            {{ iaDoProfissionalAtiva(p) ? 'IA ligada' : 'IA desligada' }}
          </span>
          <button @click="$emit('configurar', p.id)" class="text-xs text-primary hover:underline">
            Configurar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useProfissionais, iaDoProfissionalAtiva, type Profissional } from '~/composables/useProfissionais'
import { useAssistentesProfissionais } from '~/composables/useAssistentesProfissionais'

defineEmits<{ configurar: [profissionalId: string] }>()

const { profissionais, isLoading, fetchProfissionais } = useProfissionais()
const { salvar } = useAssistentesProfissionais()

let toast: any
const ligando = ref<string | null>(null)

onMounted(async () => {
  toast = await useToastSafe()
  await fetchProfissionais()
})

function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/)
  return ((partes[0]?.[0] || '') + (partes[1]?.[0] || '')).toUpperCase()
}

async function alternar(p: Profissional) {
  const alvo = !iaDoProfissionalAtiva(p)
  ligando.value = p.id
  try {
    await salvar(p.id, { ativo: alvo })
    toast?.success(alvo ? `IA de ${p.nome} ligada` : `IA de ${p.nome} desligada`)
    await fetchProfissionais({ silent: true })
  } catch (e: any) {
    toast?.error(e?.message || 'Erro ao alterar a IA')
  } finally {
    ligando.value = null
  }
}
</script>
