<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useConversas, type Mensagem } from '~/composables/useConversas'

const props = defineProps<{
  mensagem: Mensagem
  nomeProfissional: string | null
}>()

const { urlAssinadaMidia } = useConversas()

const isSent = computed(() => props.mensagem.direcao === 'SENT')
const midiaUrl = ref<string | null>(null)
const carregandoMidia = ref(false)

onMounted(async () => {
  const path = props.mensagem.midia && !Array.isArray(props.mensagem.midia)
    ? props.mensagem.midia.storage_path
    : null
  if (!path) return
  carregandoMidia.value = true
  midiaUrl.value = await urlAssinadaMidia(path)
  carregandoMidia.value = false
})

const rotuloRemetente = computed(() => {
  switch (props.mensagem.enviado_por) {
    case 'assistant': return { texto: '🤖 IA', cor: 'text-violet-200' }
    case 'celular': return { texto: `📱 ${props.nomeProfissional || 'Profissional'}`, cor: 'text-emerald-100' }
    default: return null
  }
})

const horaFormatada = computed(() => {
  try {
    return new Date(props.mensagem.data_hora).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
})
</script>

<template>
  <div class="flex" :class="isSent ? 'justify-end' : 'justify-start'">
    <div
      class="max-w-[78%] rounded-2xl px-3.5 py-2 text-sm shadow-sm"
      :class="isSent
        ? 'bg-primary text-primary-foreground rounded-br-sm'
        : 'bg-card border border-border text-foreground rounded-bl-sm'"
    >
      <p v-if="rotuloRemetente" class="text-[11px] font-semibold mb-1" :class="rotuloRemetente.cor">
        {{ rotuloRemetente.texto }}
      </p>

      <!-- Citação -->
      <div v-if="mensagem.reply_to_wa_id" class="mb-1.5 pl-2 border-l-2 text-xs opacity-70" :class="isSent ? 'border-primary-foreground/40' : 'border-border'">
        {{ mensagem.reply_to_text || 'mensagem citada' }}
      </div>

      <!-- Áudio -->
      <div v-if="mensagem.kind === 'audio'">
        <audio v-if="midiaUrl" :src="midiaUrl" controls class="max-w-[220px] h-9" />
        <p v-else class="text-xs opacity-70">{{ carregandoMidia ? 'Carregando áudio…' : '🎵 Áudio indisponível' }}</p>
      </div>

      <!-- Imagem / sticker -->
      <div v-else-if="mensagem.kind === 'image' || mensagem.kind === 'sticker'">
        <img v-if="midiaUrl" :src="midiaUrl" class="rounded-lg max-w-full max-h-64 object-contain" :class="mensagem.kind === 'sticker' ? 'max-w-[96px] max-h-[96px]' : ''" />
        <p v-else class="text-xs opacity-70">{{ carregandoMidia ? 'Carregando imagem…' : '📷 Imagem indisponível' }}</p>
        <p v-if="mensagem.mensagem" class="mt-1 whitespace-pre-wrap break-words">{{ mensagem.mensagem }}</p>
      </div>

      <!-- Vídeo -->
      <div v-else-if="mensagem.kind === 'video'">
        <video v-if="midiaUrl" :src="midiaUrl" controls class="rounded-lg max-w-full max-h-64" />
        <p v-else class="text-xs opacity-70">{{ carregandoMidia ? 'Carregando vídeo…' : '🎥 Vídeo indisponível' }}</p>
      </div>

      <!-- Documento -->
      <a
        v-else-if="mensagem.kind === 'document'"
        :href="midiaUrl || undefined"
        target="_blank"
        rel="noopener"
        class="flex items-center gap-2 rounded-lg p-2"
        :class="isSent ? 'bg-primary-foreground/10' : 'bg-muted/50'"
      >
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>
        <span class="text-xs truncate">{{ mensagem.arquivo_nome || 'Documento' }}</span>
      </a>

      <!-- Texto -->
      <p v-else class="whitespace-pre-wrap break-words">{{ mensagem.mensagem || '—' }}</p>

      <p class="text-[10px] mt-1 text-right opacity-60">{{ horaFormatada }}</p>
    </div>
  </div>
</template>
