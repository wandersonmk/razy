# Design do gravador de áudio — só o visual, sem lógica

Extraído de `app/components/ChatConversa.vue` (Razy), estado atual (pós-ajustes
de cronômetro e responsividade). São **4 blocos independentes**, um por estado
do gravador — cada um é um `<div>` que aparece no lugar da barra normal do
composer enquanto aquele estado estiver ativo.

Framework: Vue 3 + Tailwind. Os `@click="nomeDaFuncao"` e as condições
(`estadoAudio === 'recording'`) ficam nos exemplos de propósito — são a
documentação de que nome de variável/função cada bloco espera. A lógica em si
(gravar de verdade, mandar pro servidor etc.) não está aqui; é só trocar os
nomes pelos da sua própria implementação.

---

## Contrato esperado (nomes usados nos exemplos abaixo)

| Nome | Tipo | Para quê |
|---|---|---|
| `estadoAudio` | `'idle' \| 'recording' \| 'recorded' \| 'uploading'` | qual bloco mostrar |
| `tempoGravacao` | `number` (segundos) | cronômetro durante a gravação |
| `audioUrl` | `string \| null` | URL local do áudio gravado (`URL.createObjectURL`), pro player |
| `canalConectado` | `boolean` | desabilita o botão do mic se o canal estiver offline |
| `iniciarGravacao()` | função | começa a gravar |
| `pararGravacao()` | função | encerra a gravação → vai pro estado "pronto" |
| `cancelarGravacao()` | função | descarta e volta pro estado normal |
| `enviarAudioGravado()` | função | envia o áudio gravado |
| `formatarCronometro(seg)` | função | `123` → `"02:03"` |

---

## 1. Botão de microfone (gatilho — estado ocioso)

```html
<button
  v-if="!imagensPendentes.length"
  @click="iniciarGravacao"
  :disabled="!canalConectado"
  title="Gravar áudio"
  class="w-10 h-10 rounded-lg grid place-items-center text-muted-foreground hover:text-foreground hover:bg-muted transition disabled:opacity-40 shrink-0"
>
  <svg class="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" />
  </svg>
</button>
```

---

## 2. Gravando

Ponto vermelho pulsante (`animate-pulse`, utilitário nativo do Tailwind — não
precisa de `@keyframes` custom), cronômetro em `tabular-nums` (os dígitos não
"dançam" a cada segundo porque têm largura fixa), e dois botões de texto.

```html
<div v-if="estadoAudio === 'recording'" class="flex items-center gap-3 border border-input rounded-xl bg-background px-3.5 py-2 min-h-[40px]">
  <span class="w-2 h-2 rounded-full bg-red-500 shrink-0 animate-pulse" />
  <span class="text-sm font-bold tabular-nums text-foreground">{{ formatarCronometro(tempoGravacao) }}</span>
  <span class="text-xs text-muted-foreground flex-1">Gravando áudio...</span>
  <button @click="cancelarGravacao" class="text-xs font-semibold text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted shrink-0">Cancelar</button>
  <button @click="pararGravacao" class="text-xs font-semibold text-destructive hover:bg-destructive/10 px-2 py-1 rounded-md shrink-0">Parar</button>
</div>
```

---

## 3. Áudio pronto (revisar antes de enviar)

Player nativo (`<audio controls>`) ocupando o espaço disponível, com três
ações — descartar, regravar, enviar.

```html
<div v-else-if="estadoAudio === 'recorded'" class="flex items-center gap-2 border border-input rounded-xl bg-background px-3 py-1.5 min-h-[40px]">
  <audio v-if="audioUrl" :src="audioUrl" controls class="h-9 flex-1 min-w-0" />
  <button @click="cancelarGravacao" class="text-xs font-semibold text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted shrink-0">Descartar</button>
  <button @click="cancelarGravacao(); iniciarGravacao()" class="text-xs font-semibold text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted shrink-0">Regravar</button>
  <button @click="enviarAudioGravado" class="text-xs font-bold text-primary hover:bg-primary/10 px-2.5 py-1.5 rounded-md shrink-0">Enviar áudio</button>
</div>
```

---

## 4. Enviando

Spinner (mesmo ícone giratório usado no botão de enviar texto, pra manter o
mesmo "vocabulário visual" em todo o composer).

```html
<div v-else-if="estadoAudio === 'uploading'" class="flex items-center gap-2.5 border border-input rounded-xl bg-background px-3.5 py-2 min-h-[40px] text-sm text-muted-foreground">
  <svg class="w-4 h-4 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
    <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
  </svg>
  Enviando áudio...
</div>
```

---

## Tokens de cor usados (se o seu app não tiver essas classes)

O Razy usa Tailwind com cores semânticas mapeadas em variáveis CSS (tema claro
e escuro automaticamente). Se o outro app não tiver essas mesmas classes,
troque pela cor equivalente do seu design system — ou pelos hex abaixo (tema
escuro, que é o padrão do Razy):

| Classe | Papel | Hex aproximado (escuro) |
|---|---|---|
| `bg-background` | fundo da barra | `#141518` |
| `border-input` | borda padrão de campo | `#26272B` |
| `text-foreground` | texto principal | `#FFFFFF` |
| `text-muted-foreground` | texto secundário/rótulo | `#A0A3AC` |
| `text-primary` / `bg-primary` | cor de marca (ação principal) | `#3B82F6` |
| `text-destructive` | vermelho de alerta/parar | `#EF4444` |
| `hover:bg-muted` | fundo sutil no hover | `#26272B` |

Todos os ícones são SVG inline (sem depender de biblioteca de ícones) e as
animações (`animate-pulse`, `animate-spin`) são utilitários nativos do
Tailwind — nada de CSS customizado precisa ser copiado junto.
