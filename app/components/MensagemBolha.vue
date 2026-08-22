<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useConversas, type Mensagem } from '~/composables/useConversas'

const props = defineProps<{
  mensagem: Mensagem
  nomeProfissional: string | null
}>()

const { urlAssinadaMidia, baixarMidia } = useConversas()

const isSent = computed(() => props.mensagem.direcao === 'SENT')
const midiaUrl = ref<string | null>(null)
const carregandoMidia = ref(false)
const lightboxAberto = ref(false)
const baixando = ref(false)

const storagePath = computed(() => {
  const m = props.mensagem.midia
  if (!m) return null
  return (Array.isArray(m) ? m[0] : m)?.storage_path || null
})

// Reativo (não onMounted-só-uma-vez): quando a mensagem chega via Realtime,
// `midia` pode ser preenchida DEPOIS que a bolha já foi montada (ver
// ChatConversa.vue) — o watch pega essa mudança e busca a signed URL na hora.
watch(
  storagePath,
  async (path) => {
    if (!path) { midiaUrl.value = null; return }
    carregandoMidia.value = true
    midiaUrl.value = await urlAssinadaMidia(path)
    carregandoMidia.value = false
  },
  { immediate: true }
)

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

const extensaoDocumento = computed(() => {
  const nome = props.mensagem.arquivo_nome || ''
  const m = nome.match(/\.([a-z0-9]{1,6})$/i)
  return m ? m[1].toLowerCase() : ''
})

const rotuloDocumento = computed(() => {
  switch (extensaoDocumento.value) {
    case 'pdf': return 'PDF'
    case 'doc': case 'docx': return 'Word'
    case 'xls': case 'xlsx': return 'Excel'
    case 'ppt': case 'pptx': return 'PowerPoint'
    default: return 'Documento'
  }
})

async function baixar() {
  if (!storagePath.value || baixando.value) return
  baixando.value = true
  try {
    await baixarMidia(storagePath.value, props.mensagem.arquivo_nome)
  } finally {
    baixando.value = false
  }
}
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
      <div v-if="mensagem.kind === 'audio'" class="flex items-center gap-1.5">
        <audio v-if="midiaUrl" :src="midiaUrl" controls class="max-w-[220px] h-9" />
        <p v-else class="text-xs opacity-70">{{ carregandoMidia ? 'Carregando áudio…' : '🎵 Áudio indisponível' }}</p>
        <button
          v-if="midiaUrl"
          @click="baixar"
          :disabled="baixando"
          title="Baixar áudio"
          class="shrink-0 p-1.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 transition disabled:opacity-50"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>
        </button>
      </div>

      <!-- Imagem / sticker -->
      <div v-else-if="mensagem.kind === 'image' || mensagem.kind === 'sticker'">
        <div v-if="midiaUrl" class="relative group inline-block">
          <img
            :src="midiaUrl"
            @click="lightboxAberto = true"
            class="rounded-lg max-w-full max-h-64 object-contain cursor-zoom-in"
            :class="mensagem.kind === 'sticker' ? 'max-w-[96px] max-h-[96px]' : ''"
          />
          <button
            v-if="mensagem.kind !== 'sticker'"
            @click="baixar"
            :disabled="baixando"
            title="Baixar imagem"
            class="absolute top-1.5 right-1.5 p-1.5 rounded-full bg-black/50 text-white opacity-0 group-hover:opacity-100 transition disabled:opacity-50"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>
          </button>
        </div>
        <p v-else class="text-xs opacity-70">{{ carregandoMidia ? 'Carregando imagem…' : '📷 Imagem indisponível' }}</p>
        <p v-if="mensagem.mensagem" class="mt-1 whitespace-pre-wrap break-words">{{ mensagem.mensagem }}</p>

        <!-- Lightbox -->
        <Teleport to="body">
          <div
            v-if="lightboxAberto && midiaUrl"
            class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm"
            @click.self="lightboxAberto = false"
          >
            <button
              @click="lightboxAberto = false"
              class="absolute top-4 right-4 p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition"
              title="Fechar"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
            <button
              @click="baixar"
              :disabled="baixando"
              class="absolute top-4 right-16 p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition disabled:opacity-50"
              title="Baixar imagem"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>
            </button>
            <img :src="midiaUrl" class="max-w-full max-h-full rounded-lg object-contain" @click.stop />
          </div>
        </Teleport>
      </div>

      <!-- Vídeo -->
      <div v-else-if="mensagem.kind === 'video'">
        <div v-if="midiaUrl" class="relative inline-block">
          <video :src="midiaUrl" controls class="rounded-lg max-w-full max-h-64" />
          <button
            @click="baixar"
            :disabled="baixando"
            title="Baixar vídeo"
            class="absolute top-1.5 right-1.5 p-1.5 rounded-full bg-black/50 text-white hover:bg-black/70 transition disabled:opacity-50"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>
          </button>
        </div>
        <p v-else class="text-xs opacity-70">{{ carregandoMidia ? 'Carregando vídeo…' : '🎥 Vídeo indisponível' }}</p>
      </div>

      <!-- Documento (PDF, Word, etc.) — só baixa, não abre viewer -->
      <button
        v-else-if="mensagem.kind === 'document'"
        @click="baixar"
        :disabled="!midiaUrl || baixando"
        class="flex items-center gap-2 rounded-lg p-2 w-full text-left disabled:opacity-60"
        :class="isSent ? 'bg-primary-foreground/10 hover:bg-primary-foreground/15' : 'bg-muted/50 hover:bg-muted'"
      >
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>
        <span class="flex-1 min-w-0">
          <span class="block text-xs truncate">{{ mensagem.arquivo_nome || rotuloDocumento }}</span>
          <span class="block text-[10px] opacity-60">{{ midiaUrl ? (baixando ? 'Baixando…' : `Toque para baixar · ${rotuloDocumento}`) : (carregandoMidia ? 'Carregando…' : 'Documento indisponível') }}</span>
        </span>
        <svg v-if="midiaUrl" class="w-4 h-4 shrink-0 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>
      </button>

      <!-- Texto -->
      <p v-else class="whitespace-pre-wrap break-words">{{ mensagem.mensagem || '—' }}</p>

      <p class="text-[10px] mt-1 text-right opacity-60">{{ horaFormatada }}</p>
    </div>
  </div>
</template>
