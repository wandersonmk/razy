# Composer manual (atendente intervindo na conversa) + pausa automática da IA

Documento de portabilidade, no mesmo espírito do `docs/analista-de-atendimento.md`.
Aqui o pedido foi mais literal: **copiar a estrutura real** (template + funções +
endpoints) da área onde o atendente/dono da empresa manda mensagem manualmente
numa conversa — texto, áudio, imagem, documento e câmera — e a mecânica de
pausa automática da IA que isso dispara. **Sticker foi excluído de propósito**
(não é para portar agora).

Tudo abaixo existe hoje em produção no Agzap. Os nomes de arquivo, tabelas e
variáveis são os reais — dá pra copiar trecho por trecho.

---

## 1. O que é / por que existe

Na página de conversas, o textarea de baixo não é só "mandar texto pro
cliente": é o ponto onde um **humano assume a conversa a qualquer momento**,
mesmo com a IA ativa. Ao mandar qualquer coisa por ali — texto, áudio, foto,
documento — duas coisas acontecem:

1. A mensagem é entregue ao cliente (via UAzAPI ou Meta Cloud API, dependendo
   do canal da conversa).
2. **A IA é pausada automaticamente** para aquele contato, por um tempo
   configurável (`agente_configuracoes.pausa_segundos`), pra não responder por
   cima do atendente.

O motivo do item 2 existir é o mesmo de sempre: se o atendente manda "vou te
enviar o boleto" e, 3 segundos depois, a IA responde a última pergunta do
cliente como se nada tivesse acontecido, o atendimento fica com dois "donos"
falando coisas desencontradas. A pausa evita isso sem exigir que o atendente
lembre de pausar manualmente toda vez.

---

## 2. Arquitetura

```
Navegador (Vue) — app/pages/conversas.vue
  │
  │ 1) INSERT direto na tabela `mensagens` via Supabase client
  │    (direcao='SENT', enviado_por='humano', enviado_por_profissional_id=...)
  │    — feedback imediato na tela, antes mesmo da entrega real
  │
  │ 2) POST /api/webhooks/{enviado | audio | arquivo}  (fire-and-forget)
  ▼
Servidor Nuxt (Nitro)
  │  detecta se a instância é Meta ou UAzAPI e chama a API certa
  │  ao terminar, chama autoBloquearContatoMeta(...)
  ▼
autoBloquearContatoMeta (server/utils/autoBloquearContato.ts)
  │  lê agente_configuracoes.pausa_segundos
  ▼
dispatchBlockContato (server/utils/aiEngine.ts)
  │  POST {LANGCHAIN_SERVICE_URL}/control/block + x-internal-token
  ▼
ai-service (FastAPI) — app/api/control.py
  │  gera as variantes de telefone (com/sem 9º dígito) e escreve no Redis
  ▼
Redis (EasyPanel) — chave `{telefone}_{empresa_sem_hifen}_{instancia_sem_hifen}_block`, TTL = pausa_segundos
```

Upload de mídia (áudio/imagem/documento) é **direto pro R2** via presigned
URL — o arquivo em si nunca passa pelo servidor Nuxt/Vercel, só o
`/api/storage/presigned-url` (gera a URL assinada) e o
`/api/storage/register-upload` (registra no banco depois do PUT). Isso evita
estourar limite de payload de function serverless com arquivo grande.

---

## 3. Estado do composer (refs do Vue)

```ts
// Texto
const mensagemTexto = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

// Áudio
const estadoAudio = ref<'idle' | 'recording' | 'recorded' | 'uploading'>('idle')
const mediaRecorder = ref<MediaRecorder | null>(null)
const audioChunks = ref<Blob[]>([])
const audioBlob = ref<Blob | null>(null)
const audioUrl = ref<string | null>(null)
const tempoGravacao = ref(0)
const intervaloGravacao = ref<ReturnType<typeof setInterval> | null>(null)
const audioMimeType = ref<string>('audio/webm')
const audioFileExtension = ref<string>('webm')

// Upload de arquivo/imagem
const estadoUpload = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const arquivoSelecionado = ref<File | null>(null)
const progressoUpload = ref(0)
const nomeArquivoUpload = ref('')
const isDraggingOver = ref(false)

// Lote (colar/arrastar várias imagens de uma vez)
const LIMITE_ARQUIVOS_LOTE = 15
const imagensPendentes = ref<Array<{ file: File, previewUrl: string }>>([])
const filaArquivosPendentes = ref<File[]>([])   // fila p/ retry com outra instância
const uploadLoteTotal = ref(0)
const uploadLoteAtual = ref(0)

// Câmera
const mostrarModalCamera = ref(false)
const cameraVideoRef = ref<HTMLVideoElement | null>(null)
const cameraCanvasRef = ref<HTMLCanvasElement | null>(null)
const fotoCapturada = ref<string | null>(null)

// Menu de anexo (dropdown do clipe)
const mostrarMenuAnexo = ref(false)     // desktop
const mostrarMenuMobile = ref(false)    // menu "⋮" mobile — agrupa emoji/anexo/PIX/IA
```

`estadoAudio` e `estadoUpload`/`imagensPendentes.length` são **mutuamente
exclusivos com o textarea normal** — o template esconde os botões de
emoji/anexo/PIX/mic enquanto qualquer um deles está ativo (`v-if="!imagensPendentes.length && estadoAudio === 'idle' && !estadoUpload"`).

---

## 4. Template — textarea + barra de ações

Estrutura real (excluindo sticker), simplificada só nos comentários:

```html
<div class="flex items-end gap-1.5 sm:gap-2 w-full min-w-0">
  <div
    class="flex-1 min-w-0 relative"
    :class="{ 'drag-over': isDraggingOver }"
    @dragover.prevent="isDraggingOver = true"
    @dragenter.prevent="isDraggingOver = true"
    @dragleave="isDraggingOver = false"
    @drop.prevent="handleDrop($event)"
  >
    <!-- Preview de imagens pendentes (uma ou várias) -->
    <div v-if="imagensPendentes.length" class="px-2 pt-2 pb-1">
      <div class="flex items-center gap-2 flex-wrap">
        <div v-for="(img, idx) in imagensPendentes" :key="img.previewUrl" class="relative flex-shrink-0 group/thumb">
          <img :src="img.previewUrl" class="h-14 w-14 object-cover rounded border border-border" />
          <button @click="removerImagemPendente(idx)" class="absolute -top-1.5 -right-1.5 ...">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      </div>
    </div>

    <textarea
      ref="textareaRef"
      v-model="mensagemTexto"
      :placeholder="/* várias condições: instância desconectada, janela Meta fechada, etc. */"
      rows="1"
      :disabled="!!imagensPendentes.length || estadoAudio !== 'idle' || (isDesconectado && !instanciasConectadas.length)"
      class="block w-full px-3 py-2 text-sm border border-input bg-background rounded-lg resize-none overflow-y-auto min-h-[40px] max-h-[10.5rem] leading-6"
      @keydown.enter="handleEnter"
      @input="handleInput"
      @paste="handlePaste($event)"
    ></textarea>
  </div>

  <!-- Input file oculto -->
  <input
    ref="fileInputRef"
    type="file"
    accept="image/*,video/mp4,video/webm,video/quicktime,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.txt,.zip,.rar,.cdr,.ai,.psd,.eps,.tif,.tiff,.indd"
    multiple
    @change="handleFileSelect"
    class="hidden"
  />

  <!-- Botão de anexo (clipe) + dropdown -->
  <div class="relative flex-shrink-0 hidden sm:block" @click.stop>
    <div v-if="mostrarMenuAnexo" class="absolute z-50 bg-popover border border-border rounded-xl shadow-xl ...">
      <button @click="abrirSeletorArquivo(); mostrarMenuAnexo = false">Buscar arquivo</button>
      <button @click="abrirCamera(); mostrarMenuAnexo = false">Tirar foto</button>
      <!-- (sticker fica de fora do escopo desta portabilidade) -->
    </div>
    <button @click.stop="isTouchDevice ? abrirSeletorArquivo() : (mostrarMenuAnexo = !mostrarMenuAnexo)" title="Enviar arquivo">
      <!-- ícone de clipe -->
    </button>
  </div>

  <!-- Botão de microfone -->
  <button v-if="!imagensPendentes.length && estadoAudio === 'idle'" @click="iniciarGravacao" title="Gravar áudio">
    <!-- ícone de microfone -->
  </button>

  <!-- Botão de enviar -->
  <button v-if="!imagensPendentes.length && estadoAudio === 'idle'" @click="enviarMensagem()">
    <!-- ícone de enviar -->
  </button>
</div>
```

**Detalhes que não são cosméticos:**

- `rows="1"` + `autoResize()` no `@input`: o textarea cresce até 8 linhas
  (`lineHeight * maxLines`) e depois vira scroll interno — nunca empurra o
  layout pra fora da tela.
- `@keydown.enter="handleEnter"`: Enter sozinho envia; **Shift+Enter** quebra
  linha. Também é o handler que confirma a seleção de atalho (`/comando`)
  quando o dropdown de atalhos está aberto.
- `@paste="handlePaste($event)"` + um listener de `paste` no `document`
  (`handlePasteDocumento`, registrado em `onMounted`): permite colar uma
  imagem do clipboard (Ctrl+V) mesmo sem focar o textarea, desde que o foco
  não esteja em outro input/textarea/contenteditable.
- `@drop.prevent="handleDrop($event)"`: arrastar arquivo pra cima do
  composer. Imagem/vídeo vira preview pendente (mesma UX do colar); qualquer
  outro tipo (PDF, DOCX...) já dispara o envio direto.

---

## 5. Enviar texto

```ts
const handleEnter = (e: KeyboardEvent) => {
  if (mostrarAtalhos.value && atalhosFiltrados.value.length > 0) {
    e.preventDefault()
    selecionarAtalho(atalhosFiltrados.value[atalhoSelecionadoIndex.value])
    return
  }
  if (!e.shiftKey) {
    e.preventDefault()
    enviarMensagem()
  } else {
    setTimeout(() => autoResize(), 0)
  }
}

const enviarMensagem = async (instanciaOverrideId?: string | null) => {
  const texto = mensagemTexto.value.trim()
  if (!texto || !conversaSelecionada.value) return

  // limpa o textarea ANTES do trabalho assíncrono (feedback imediato)
  mensagemTexto.value = ''

  // resolve empresa_id (usuarios_empresas -> fallback empresas.auth_user_id)
  // resolve instancia_id / numero_conectado da conversa
  // ...

  const { data: mensagemInserida } = await supabase.from('mensagens').insert({
    conversa_id: conversaId,
    numero: conversaSelecionada.value.telefone,
    mensagem: texto,
    direcao: 'SENT',
    nome_contato: conversaSelecionada.value.nome,
    data_hora: new Date().toISOString(),
    chatlid: conversaSelecionada.value.chatlid,
    empresa_id: empresaId,
    enviado_por: 'humano',
    enviado_por_profissional_id: meuProfissionalId.value || null,
    mensagem_assinada: assinarMensagem.value,
    instancia_id: instanciaIdFinal,
  }).select().single()

  mensagens.value.push(mensagemInserida)
  await abrirConversaAutomaticamente(conversaId)   // auto-atribui a conversa a este atendente
  marcarPausaOtimista(conversaId)                  // badge "IA pausada" na hora, sem esperar o webhook
  scrollToBottom()

  // fire-and-forget: a entrega real acontece aqui, mas a UI já não espera
  void $fetch(isMetaInstance ? '/api/webhooks/enviado-meta' : '/api/webhooks/enviado', {
    method: 'POST',
    body: { telefone, mensagem: texto, mensagem_id: mensagemInserida.id, empresa_id, instancia_id, /* ... */ },
  })
}
```

Pontos que valem a pena levar:

- **A mensagem entra no banco ANTES de ser realmente entregue.** A UI mostra
  o balão na hora (otimista); a entrega de verdade é assíncrona.
- **`enviado_por: 'humano'` + `enviado_por_profissional_id`** é o que
  diferencia essa mensagem de uma resposta da IA (`enviado_por='assistant'`)
  ou de uma mensagem mandada direto do celular do atendente
  (`enviado_por='celular'`, sem `enviado_por_profissional_id`).
- **Auto-atribuição:** se o profissional logado ainda não é o dono da
  conversa, a 1ª mensagem que ele manda já atribui a conversa a ele
  (`assigned_to_professional_id`) e grava um registro em
  `conversa_atendentes_historico` (ação `atribuido`).

---

## 6. Gravar e enviar áudio

```ts
// ═══ Gravação (MediaRecorder da API do navegador) ═══
const iniciarGravacao = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

  // Detecta o melhor codec suportado, com fallback em cascata
  let mimeType = 'audio/webm', fileExtension = 'webm'
  if (MediaRecorder.isTypeSupported('audio/ogg; codecs=opus')) {
    mimeType = 'audio/ogg; codecs=opus'; fileExtension = 'ogg'
  } else if (MediaRecorder.isTypeSupported('audio/webm; codecs=opus')) {
    mimeType = 'audio/webm; codecs=opus'; fileExtension = 'webm'
  }

  const recorder = new MediaRecorder(stream, { mimeType })
  audioChunks.value = []
  recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.value.push(e.data) }
  recorder.onstop = () => {
    const blob = new Blob(audioChunks.value, { type: mimeType })
    audioBlob.value = blob
    audioUrl.value = URL.createObjectURL(blob)
    audioMimeType.value = mimeType
    audioFileExtension.value = fileExtension
    estadoAudio.value = 'recorded'
    stream.getTracks().forEach(t => t.stop())
  }
  recorder.start()
  mediaRecorder.value = recorder
  estadoAudio.value = 'recording'
  tempoGravacao.value = 0
  intervaloGravacao.value = setInterval(() => { tempoGravacao.value++ }, 1000)
}

const pararGravacao = () => {
  if (mediaRecorder.value?.state === 'recording') {
    mediaRecorder.value.stop()
    clearInterval(intervaloGravacao.value!)
  }
}

const cancelarGravacao = () => {
  // para o recorder se ainda estiver gravando, limpa blob/url/estado -> 'idle'
}

// ═══ Envio ═══
const enviarAudio = async (instanciaOverrideId?: string | null) => {
  const MAX_AUDIO = 16 * 1024 * 1024   // limite oficial WhatsApp p/ áudio
  if (audioBlob.value.size > MAX_AUDIO) { alert('Áudio muito grande'); cancelarGravacao(); return }

  estadoAudio.value = 'uploading'

  // 1) pede presigned URL do R2
  const presigned = await $fetch('/api/storage/presigned-url', {
    method: 'POST',
    headers: { Authorization: `Bearer ${session.access_token}` },
    body: { contentType: audioMimeType.value.split(';')[0], fileName, mensagemId, empresaId, instanciaId, tipoArquivo: 'AUDIO' },
  })

  // 2) PUT direto no R2 (não passa pelo servidor Nuxt)
  await fetch(presigned.presignedUrl, { method: 'PUT', headers: { 'Content-Type': cleanContentType }, body: audioBlob.value })

  // 3) registra o upload (best-effort, fire-and-forget)
  void $fetch('/api/storage/register-upload', { method: 'POST', headers: {...}, body: { storagePath: presigned.storagePath, mensagemId, empresaId, instanciaId, publicUrl: presigned.publicUrl } })

  // 4) insere a mensagem (mesmo padrão do texto: direcao SENT, enviado_por humano)
  const { data: mensagemInserida } = await supabase.from('mensagens').insert({
    id: mensagemId, conversa_id, numero, mensagem: `🎵 Áudio (${duracaoFormatada})`,
    audio_url: presigned.publicUrl, audio_duracao: duracao, direcao: 'SENT',
    enviado_por: 'humano', enviado_por_profissional_id: meuProfissionalId.value || null,
    empresa_id, instancia_id,
  }).select().single()

  mensagens.value.push(mensagemInserida)
  await abrirConversaAutomaticamente(conversaId)

  // 5) dispara a entrega real + pausa da IA
  await $fetch('/api/webhooks/audio', { method: 'POST', body: { telefone, audio_url, duracao, mensagem_id, empresa_id, instancia_id, /* ... */ } })

  cancelarGravacao()  // reseta o estado pra 'idle'
}
```

Painel de UI por estado (`estadoAudio`):

| Estado | O que mostra |
|---|---|
| `recording` | pulso vermelho + cronômetro + botões "Cancelar" / "Parar" |
| `recorded` | player `<audio controls>` + botões "Descartar" / "Regravar" / "Enviar Áudio" |
| `uploading` | spinner + "Enviando áudio..." |

---

## 7. Anexar e enviar imagem / documento / foto da câmera

```ts
// Seleção via input file
const handleFileSelect = (event: Event) => {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  if (files.length) void enviarArquivos(files)
}

// Drag & drop: imagem/vídeo -> preview pendente; qualquer outro tipo -> envio direto
const handleDrop = (event: DragEvent) => {
  const files = Array.from(event.dataTransfer?.files || [])
  const visuais = files.filter(f => f.type.startsWith('image/') || f.type.startsWith('video/'))
  if (visuais.length) void adicionarImagensPendentes(visuais)
  const documentos = files.filter(f => !f.type.startsWith('image/') && !f.type.startsWith('video/'))
  if (documentos.length) void enviarArquivos(documentos)
}

// Colar (Ctrl+V) cai na mesma fila de "imagens pendentes"
const adicionarImagensPendentes = async (files: File[]) => {
  const vagas = LIMITE_ARQUIVOS_LOTE - imagensPendentes.value.length   // limite: 15
  for (const file of files.slice(0, Math.max(0, vagas))) {
    imagensPendentes.value.push({ file, previewUrl: URL.createObjectURL(file) })
  }
}

// Envia um LOTE reaproveitando o fluxo de 1 arquivo, sequencialmente
// (preserva a ordem das mensagens no WhatsApp e não sobrecarrega o upload)
const enviarArquivos = async (files: File[], instanciaOverrideId?: string | null) => {
  uploadLoteTotal.value = files.length
  for (let i = 0; i < files.length; i++) {
    uploadLoteAtual.value = i + 1
    arquivoSelecionado.value = files[i]
    await enviarArquivo(instanciaOverrideId)
    if (i < files.length - 1) await new Promise(r => setTimeout(r, 600))  // não atropela o reset visual
  }
  uploadLoteTotal.value = 0
}

const enviarArquivo = async (instanciaOverrideId?: string | null) => {
  const file = arquivoSelecionado.value
  const tipoArquivo = determinarTipoArquivo(file)   // 'IMAGEM' | 'VIDEO' | 'ARQUIVO' (documento)

  // Limites oficiais do WhatsApp, por tipo
  const MAX_IMAGEM = 5  * 1024 * 1024
  const MAX_VIDEO  = 16 * 1024 * 1024
  const MAX_OUTROS = 50 * 1024 * 1024
  // ... valida e aborta com alert() se estourar

  estadoUpload.value = true
  // mesmo padrão do áudio: presigned URL -> PUT direto no R2 -> register-upload
  // -> INSERT em `mensagens` (mensagem = publicUrl, arquivo_nome = nome original)
  // -> POST /api/webhooks/arquivo (entrega real + pausa da IA)
}
```

**Câmera (tirar foto sem sair do WhatsApp Web):**

```ts
const abrirCamera = async () => {
  mostrarModalCamera.value = true
  await nextTick()
  cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: cameraFacingMode } })
  cameraVideoRef.value!.srcObject = cameraStream
}

const tirarFoto = () => {
  // desenha o <video> atual num <canvas> oculto e converte pra dataURL
  const ctx = cameraCanvasRef.value!.getContext('2d')
  ctx.drawImage(cameraVideoRef.value!, 0, 0, w, h)
  fotoCapturada.value = cameraCanvasRef.value!.toDataURL('image/jpeg', 0.9)
}
// "Enviar" converte o dataURL de volta pra File e cai no mesmo enviarArquivo()
```

`cameraFacingMode` começa em `'environment'` (câmera traseira no celular) e
tem um botão pra trocar (`trocarCamera`).

---

## 8. Os 3 endpoints de saída (server-side)

| Endpoint | Envia | Roteamento |
|---|---|---|
| `POST /api/webhooks/enviado` | texto (UAzAPI) | `empresas.engine_ia` |
| `POST /api/webhooks/enviado-meta` | texto (Meta oficial) | sempre Meta Cloud API |
| `POST /api/webhooks/audio` | áudio | detecta Meta pela `instancia_id`; senão UAzAPI |
| `POST /api/webhooks/arquivo` | imagem/vídeo/documento | idem |

Os três (`audio`, `arquivo`, `enviado`) seguem o **mesmo esqueleto**:

```ts
export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const supabase = createClient(url, serviceRoleKey, { auth: { persistSession: false } })

  // 1) Essa instancia_id é Meta oficial? (consulta instancias_meta)
  const isMetaInstance = /* select id, phone_number_id from instancias_meta where id = instanciaId */

  if (isMetaInstance) {
    // chama a Meta Cloud API direto (sendImageMessage/sendDocumentMessage/sendAudioMessage/...)
    // salva meta_wamid + meta_status='sent' na linha da mensagem
    await autoBloquearContatoMeta({ supabase, empresaId, instanciaId, telefone, conversaId, ultimaMensagem })
    return { ok: true, wamid, via: 'meta-direct' }
  }

  // 2) UAzAPI — só roda direto se a empresa está em engine_ia='langchain'
  const engine = await getEngineForEmpresa(empresaId)
  if (engine === 'langchain') {
    const instanciaToken = await resolveInstanciaToken(instanciaId)
    const result = await sendComEnderecoSeguro({ telefone, chatlid }, (numero) =>
      sendImageUazapi({ token: instanciaToken, numero, imageUrl, caption })   // ou sendDocumentUazapi/sendAudioUazapi/sendTextUazapi
    )
    // grava wa_message_id retornado (necessário p/ tique de entrega/leitura
    // e p/ citação nativa quando o cliente responder esta mensagem)
    await autoBloquearContatoMeta({ supabase, empresaId, instanciaId, telefone, conversaId, ultimaMensagem })
    return { ok: true, via: 'uazapi-direct', response: result }
  }

  // 3) Fluxo legado: encaminha pro webhook n8n (mantido por compatibilidade)
})
```

Duas decisões que valem registrar:

- **`sendComEnderecoSeguro({ telefone, chatlid }, fn)`**: tenta endereçar pelo
  `@lid` quando ele existe (evita entrega cruzada entre contatos que
  compartilham `@lid`), com fallback pro telefone puro.
- **Persistir o `wa_message_id`** de volta na linha que o front já inseriu é
  o que faz o tique de entregue/lido avançar — sem isso a mídia enviada pelo
  app ficava travada num tique só (medido: 0% de 92 envios via app vs 61%
  via celular, antes do fix).

---

## 9. Pausa automática da IA — o núcleo pedido

### 9.1 Disparo (`server/utils/autoBloquearContato.ts`, arquivo inteiro)

```ts
export async function autoBloquearContatoMeta(params: {
  supabase: SupabaseClient
  empresaId: string
  instanciaId: string
  telefone: string
  conversaId?: string | null
  ultimaMensagem?: string | null
}) {
  const { supabase, empresaId, instanciaId, telefone, conversaId, ultimaMensagem } = params
  if (!empresaId || !instanciaId || !telefone) return

  const FALLBACK_PAUSA_24H = 86400
  let bloqueioSegundos: number | null = null

  // 1) pausa_segundos da config desta instância específica
  const { data: configInst } = await supabase
    .from('agente_configuracoes')
    .select('pausa_segundos')
    .eq('empresa_id', empresaId)
    .eq('instancia_id', instanciaId)
    .maybeSingle()
  if (configInst?.pausa_segundos > 0) bloqueioSegundos = configInst.pausa_segundos
  else {
    // 2) fallback: config mais recente da empresa (qualquer instância)
    const { data: configEmpresa } = await supabase
      .from('agente_configuracoes')
      .select('pausa_segundos, updated_at')
      .eq('empresa_id', empresaId)
      .order('updated_at', { ascending: false, nullsFirst: false })
      .limit(1).maybeSingle()
    if (configEmpresa?.pausa_segundos > 0) bloqueioSegundos = configEmpresa.pausa_segundos
  }
  if (!bloqueioSegundos) bloqueioSegundos = FALLBACK_PAUSA_24H   // nunca fica sem pausa nenhuma

  // AGUARDA o dispatch (await, não fire-and-forget) — ver nota abaixo
  await dispatchBlockContato({ empresaId, instanciaId, telefone, segundos: bloqueioSegundos, conversaId, ultimaMensagem })
}
```

> **Por que `await` e não fire-and-forget:** em serverless (Vercel), uma
> promise disparada e esquecida (`void fn()`) congela quando a resposta HTTP
> já foi mandada, e só termina de rodar quando a instância "acorda" de novo —
> a pausa chegava com minutos de atraso, e nesse intervalo a IA respondia por
> cima do atendente. Isso NÃO é opcional: o `dispatchBlockContato` tem que
> ser aguardado antes do handler responder.

### 9.2 Chamada ao ai-service (`server/utils/aiEngine.ts`, trechos relevantes)

```ts
export const MAX_PAUSA_SEGUNDOS = 31_536_000   // 1 ano — teto aceito pelo ai-service

export async function dispatchBlockContato(args: {
  empresaId: string; instanciaId: string; telefone: string; segundos: number
  conversaId?: string | null; ultimaMensagem?: string | null
  manual?: boolean   // true = pausa MANUAL (operador no card), não pode ser rebaixada
}) {
  const telefoneNorm = String(args.telefone || '').replace(/\D/g, '')
  // CLAMP: config de pausa acima de 1 ano fazia o endpoint devolver 422 e a
  // pausa NUNCA era aplicada (erro engolido silenciosamente). Sempre clampar.
  const segundosClamped = Math.min(Math.max(1, Math.floor(args.segundos)), MAX_PAUSA_SEGUNDOS)

  await callAiService({
    path: '/control/block',
    body: {
      telefone: telefoneNorm, empresa_id: args.empresaId, instancia_id: args.instanciaId,
      segundos: segundosClamped, conversa_id: args.conversaId ?? null,
      ultima_mensagem: args.ultimaMensagem ?? null, manual: args.manual ?? false,
    },
  })
}

// callAiService: POST no LANGCHAIN_SERVICE_URL + header x-internal-token,
// com timeout de 12s e até 2 retries com backoff (só em erro de rede/5xx —
// erro 4xx é determinístico e não repete).
```

### 9.3 Endpoint `/control/block` no ai-service (Python/FastAPI)

`ai-service/app/api/control.py`:

```python
def _normaliza_55(numero: str) -> str:
    """Garante prefixo 55 (BR)."""
    d = re.sub(r"\D", "", numero or "")
    return d if d.startswith("55") else f"55{d}"

class BlockBody(BaseModel):
    telefone: str
    empresa_id: str
    instancia_id: str
    segundos: int = Field(gt=0, le=31_536_000)
    conversa_id: str | None = None
    ultima_mensagem: str | None = None
    manual: bool = False   # True = pausa manual autoritativa

@router.post("/block")
async def block_contato(body: BlockBody, x_internal_token: str | None = Header(...)):
    _check_auth(x_internal_token)   # compara com INTERNAL_TOKEN
    telefone_norm = _normaliza_55(body.telefone)

    # gera as chaves de TODAS as variantes de 9º dígito (ver 9.4)
    sids = session_ids_for(telefone_norm, body.empresa_id, body.instancia_id)

    if body.manual:
        # pausa manual força TODAS as identidades equivalentes
        for sid in sids:
            await set_block_manual(sid, body.segundos)
    else:
        # pausa automática NÃO sobrescreve uma pausa manual ativa
        if not await has_manual_block_any(sids):
            for sid in sids:
                await set_block(sid, body.segundos)

    # espelha o tempo de pausa na tabela `conversas` (pra UI mostrar o badge)
    update_conversa_pausa(instancia_id=body.instancia_id, segundos=body.segundos,
                           conversa_id=body.conversa_id, numero=telefone_norm,
                           set_inicio=True, ultima_mensagem=body.ultima_mensagem)
    return {"ok": True, "keys": [block_key(s) for s in sids], "ttl": body.segundos}
```

### 9.4 A chave Redis e o problema do 9º dígito

```python
# ai-service/app/memory/redis_chat.py
def build_session_id(telefone: str, empresa_id: str, instancia_id: str) -> str:
    return f"{telefone}_{empresa_id.replace('-', '')}_{instancia_id.replace('-', '')}"

def block_key(session_id: str) -> str:
    return f"{session_id}_block"

def manual_block_key(session_id: str) -> str:
    return f"{session_id}_block_manual"

async def set_block(session_id: str, ttl_seconds: int) -> None:
    if ttl_seconds <= 0: return
    await get_redis().set(block_key(session_id), "true", ex=ttl_seconds)

async def set_block_manual(session_id: str, ttl_seconds: int) -> None:
    """Grava o _block normal E um marcador _block_manual com o MESMO TTL —
    o marcador impede pausa automática de rebaixar essa pausa manual."""
    r = get_redis()
    await r.set(block_key(session_id), "true", ex=ttl_seconds)
    await r.set(manual_block_key(session_id), "1", ex=ttl_seconds)

def session_ids_for(telefone: str, empresa_id: str, instancia_id: str) -> list[str]:
    """session_ids para TODAS as variantes de 9º dígito do telefone."""
    variantes = tel_vars(telefone) or [telefone]
    return [build_session_id(t, empresa_id, instancia_id) for t in variantes]

async def is_blocked_any(session_ids: list[str]) -> bool:
    """True se QUALQUER variante estiver bloqueada."""
    for sid in session_ids:
        if (await get_redis().get(block_key(sid))) is not None:
            return True
    return False

async def has_manual_block_any(session_ids: list[str]) -> bool: ...  # mesma lógica, chave _block_manual

async def clear_block_many(session_ids: list[str]) -> int:
    """Apaga _block (e _block_manual) de TODAS as variantes. Retorna quantas sumiram."""
    r = get_redis()
    removed = int(await r.delete(*[block_key(sid) for sid in session_ids]))
    await r.delete(*[manual_block_key(sid) for sid in session_ids])
    return removed
```

**Por que existem variantes com e sem o 9º dígito:** a UAzAPI entrega o
telefone **sem** o nono dígito pra alguns DDDs interioranos (ex.: 75, 71),
enquanto o banco/front grava o número **com** o 9. A mesma pessoa aparece
como `5575991198502` (banco/front) e `557591198502` (payload UAzAPI). Se o
bloqueio é gravado numa forma e checado/apagado só na outra, o resultado é:
badge "IA pausada" que não aparece, ou desbloqueio que roda mas
`removed=0` (a IA continua muda pro cliente, ou continua falando por cima do
atendente). A função que gera as variantes:

```python
# ai-service/app/utils/normalize.py
def tel_vars(value: str | None) -> list[str]:
    """Variantes BR do telefone com/sem o nono dígito do celular."""
    d = re.sub(r"\D", "", value or "")
    if not d:
        return []
    out = [d]

    # Caso internacional +1 salvo como se fosse BR pelo normalizador legado
    # (payload UAzAPI: 17015557208 / banco: 5517015557208) — tratado como
    # alias da mesma sessão, sem confundir número BR válido.
    br_prefixado_invalido = d.startswith("55") and len(d) in (12, 13) and d[4] in "01"
    if br_prefixado_invalido:
        out.append(d[2:])
    elif len(d) == 11 and d.startswith("1") and ("55" + d)[4] in "01":
        out.append("55" + d)
    elif d.startswith("55") and len(d) == 13:      # 55 DD 9 XXXXXXXX -> sem o 9
        out.append(d[:4] + d[5:])
    elif d.startswith("55") and len(d) == 12:      # 55 DD XXXXXXXX -> com o 9
        out.append(d[:4] + "9" + d[4:])

    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]
```

Essa mesma função (`tel_vars`) é usada em **quatro lugares diferentes** —
bloquear, desbloquear, checar se está bloqueado (`is_blocked_any`, no
`dispatcher.py`, antes da IA responder um inbound) e limpar memória
(`/control/clear-memory`). Usar variantes em só um dos quatro pontos já é o
suficiente pra reintroduzir o bug.

### 9.5 Desbloqueio (`/control/unblock`)

```python
@router.post("/unblock")
async def unblock_contato(body: UnblockBody, x_internal_token=Header(...)):
    _check_auth(x_internal_token)
    telefone_norm = _normaliza_55(body.telefone)
    sids = session_ids_for(telefone_norm, body.empresa_id, body.instancia_id)
    removed = await clear_block_many(sids)   # apaga TODAS as variantes de uma vez
    update_conversa_pausa(instancia_id=body.instancia_id, segundos=0,
                           conversa_id=body.conversa_id, numero=telefone_norm, set_inicio=False)
    return {"ok": True, "removed": int(removed)}
```

### 9.6 Pausa manual × pausa automática

Duas origens diferentes escrevem a mesma chave Redis:

| Origem | `manual=` | Pode ser rebaixada? |
|---|---|---|
| Atendente manda mensagem pelo **app** (composer) ou pelo **celular** | `false` | Sim — é a automática de todo dia |
| Operador clica em "Bloquear/Restringir" no card da conversa | `true` | Não — grava `_block_manual` junto, e pausas automáticas **checam esse marcador antes de sobrescrever** |

Isso evita que uma pausa manual de "10 dias" (porque o dono decidiu atender
esse cliente pessoalmente por um tempo) seja derrubada pela primeira mensagem
automática de 15 minutos assim que o atendente manda "oi" ali no meio.

### 9.7 Pausa otimista no front (badge instantâneo)

O `/control/block` real é assíncrono (rede até o ai-service). Pra o
atendente não ver "IA Ativa" por 1-2 segundos logo depois de mandar a
mensagem, o front marca a pausa **localmente antes** da confirmação:

```ts
const marcarPausaOtimista = (convId: string) => {
  const agoraIso = new Date().toISOString()
  const aplicar = (c: any) => {
    if (c && getTempoRestante(c) <= 0) {
      c.tempo_pausa = 86400          // 24h "de exibição" — o valor real
      c.tempo_pausa_inicio = agoraIso // chega pelo realtime e substitui isso
    }
  }
  if (conversaSelecionada.value?.id === convId) aplicar(conversaSelecionada.value)
  const idx = conversas.value.findIndex((c: any) => c.id === convId)
  if (idx !== -1) aplicar(conversas.value[idx])
}
```

O valor real (`pausa_segundos` configurado) chega pouco depois via
Realtime/refetch e substitui o otimista — sem esse truque, a UI mostrava
"IA Ativa" bem na hora em que o atendente mais precisa ter certeza de que
assumiu a conversa.

### 9.8 Nota: a mesma pausa também dispara quando o atendente usa o CELULAR

Fora do escopo pedido (composer do app), mas explica por que a checagem
cobre as duas formas de número: quando o atendente responde **direto pelo
WhatsApp do celular** (não pelo app), o evento chega como um inbound
`fromMe=true` da UAzAPI, tratado por `handle_from_me`
(`ai-service/app/worker/dispatcher.py`) — que insere a mensagem com
`enviado_por='celular'` e chama o **mesmo** `set_block`/`session_id` acima.
Ou seja: **duas origens diferentes (app e celular) escrevem a mesma chave
Redis**, e é exatamente por isso que gerar/checar todas as variantes de 9º
dígito importa nos dois casos.

---

## 10. Limites e validações

| Tipo | Limite | Onde é validado |
|---|---|---|
| Áudio | 16 MB (limite oficial WhatsApp Business API) | front, antes do upload |
| Vídeo | 16 MB | front |
| Imagem | 5 MB | front |
| Documento/outros | 50 MB | front |
| Arquivos por lote (colar/arrastar) | 15 | front (`LIMITE_ARQUIVOS_LOTE`) |
| Extensões aceitas no seletor de arquivo | `image/*, video/mp4, video/webm, video/quicktime, .pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .csv, .txt, .zip, .rar, .cdr, .ai, .psd, .eps, .tif, .tiff, .indd` | atributo `accept` do `<input type="file">` |

Codec de áudio: tenta `audio/ogg; codecs=opus` primeiro (melhor compatibilidade
com a Meta Cloud API, evita transcodificação), cai pra `audio/webm; codecs=opus`
e por último `audio/webm` genérico, conforme o que `MediaRecorder.isTypeSupported`
aceitar no navegador do atendente.

---

## 11. Variáveis de ambiente envolvidas

```
# Nuxt
SUPABASE_SERVICE_ROLE_KEY=...      # bypassa RLS nos 3 endpoints de webhook
LANGCHAIN_SERVICE_URL=https://...  # base URL do ai-service
LANGCHAIN_INTERNAL_TOKEN=...       # tem que bater com INTERNAL_TOKEN do ai-service
META_SYSTEM_TOKEN=...              # fallback quando a instância Meta não tem token próprio

# ai-service
INTERNAL_TOKEN=...                 # valida o header x-internal-token
REDIS_URL=...                      # instância self-hosted (EasyPanel)
```

---

## 12. Checklist para portar

- [ ] Existe uma tabela `mensagens` com `direcao` (SENT/RECEIVED) e
      `enviado_por` (para diferenciar humano/app, humano/celular e IA)?
- [ ] Upload de mídia vai DIRETO pro storage (presigned URL), sem passar o
      arquivo binário pela function serverless?
- [ ] A pausa da IA é uma chave com TTL (Redis ou equivalente), não uma
      coluna que alguém precisa lembrar de zerar depois?
- [ ] A chave da pausa cobre **todas as variantes de formatação de telefone**
      que o seu provedor de WhatsApp pode entregar (9º dígito é o caso do
      Brasil; outros países têm as próprias pegadinhas)?
- [ ] Pausa manual (operador) e pausa automática (atendente respondeu) são
      **marcadores diferentes**, com a automática nunca rebaixando a manual?
- [ ] O dispatch da pausa é **aguardado** (`await`), não fire-and-forget —
      principalmente se o backend roda em serverless?
- [ ] A UI mostra o estado de pausa de forma otimista, sem esperar a
      confirmação de rede?
- [ ] `wa_message_id`/id retornado pelo provedor é salvo de volta na
      mensagem, para tique de entrega/leitura e citação funcionarem?

---

## 13. Fora do escopo (de propósito)

- **Sticker** — existe no Agzap (`abrirStickerPicker`, biblioteca de figurinhas
  da empresa, conversão pra `.webp`/`.png`), mas foi explicitamente deixado
  de fora deste documento a pedido do usuário.
- Emoji picker, atalhos de texto (`/comando`), botão de PIX e botão de
  Template Meta também vivem na mesma barra, mas são features à parte —
  citados aqui só onde apareciam no meio do código relevante.
