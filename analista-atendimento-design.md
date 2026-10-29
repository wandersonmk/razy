# Analista de Atendimento — design completo (CSS, Tailwind, cards, gráficos, PDF)

Documento de portabilidade entre os dois apps. Objetivo: reproduzir no outro
aplicativo **exatamente o mesmo visual** do Analista de Atendimento do Razy —
a bolha, o painel lateral, a tela de abertura com os cards de pergunta, os
cards temáticos de resposta, os gráficos e a exportação em PDF.

Tudo abaixo existe hoje em produção no Razy. Arquivos reais:

| Arquivo | Papel |
|---|---|
| `app/components/AnalistaAtendimento.vue` | bolha + painel lateral + tela de abertura + exportação |
| `app/components/CardAnalista.vue` | um card temático da resposta |
| `app/components/GraficoAnalista.vue` | um gráfico (chart.js) da resposta |
| `app/composables/useAnalista.ts` | estado, chamada da API e **toda a geração de PDF** |
| `app/composables/useConversaAtiva.ts` | conversa aberta na tela → contexto do painel |
| `server/api/analista/perguntar.post.ts` | proxy Nuxt → ai-service |
| `server/api/analista/resumo.get.ts` | proxy Nuxt → ai-service (números da abertura) |
| `ai-service/app/services/analista.py` | orquestra LLM + ferramentas, **monta os cards por código** |
| `ai-service/app/services/analista_consultas.py` | SQL fixo (as únicas portas de leitura) |
| `ai-service/app/api/analista.py` | rotas FastAPI internas |

Stack: **Vue 3 + Tailwind (darkMode: 'class')**, `chart.js@^4.5`, `jspdf@^3` +
`jspdf-autotable@^5`. Ícones são **SVG inline** (nenhuma lib de ícone).
Animações são utilitários nativos do Tailwind (`animate-spin`, `animate-pulse`).

---

## 1. Arquitetura visual

```
Layout do dashboard (app/layouts/dashboard.vue)
  └── <AnalistaAtendimento />          ← fica no layout, acompanha todas as páginas
        ├── botão flutuante (FAB)       bottom-6 / bottom-44 · right-6
        ├── véu (overlay preto)         fixed inset-0 bg-black/40
        └── <aside> painel lateral      fixed top/right/bottom · entra da direita
              ├── <header>              ícone + título + status + ampliar/nova/fechar
              ├── corpo (scroll)
              │     ├── TELA DE ABERTURA (sem turnos)
              │     │     ├── "O que você quer saber?"
              │     │     ├── card de contexto (conversa aberta)   ← opcional
              │     │     ├── 4 tiles de números                    ← do /resumo
              │     │     ├── faixa de cobertura                    ← opcional
              │     │     └── CATÁLOGO de perguntas (4 grupos)
              │     └── CONVERSA (com turnos)
              │           ├── balão do usuário (à direita)
              │           ├── faixa de cobertura do turno           ← opcional
              │           ├── <CardAnalista> × N                    ← resposta
              │           ├── <GraficoAnalista> × N                 ← opcional
              │           ├── botão "Baixar PDF"
              │           └── botão "Baixar análise completa"       ← ≥ 2 respostas
              └── <footer>              input + enviar + aviso
```

Por que **painel lateral** e não balão: a resposta é densa (visão geral tem
~10 campos, comparação de vendedores vem em tabela). Largura: `700px` normal,
`980px` ampliado, `100vw` no mobile.

Por que fica **no layout**: a pergunta quase sempre nasce olhando outra tela
("e esse cliente aqui, como está?").

---

## 2. Tokens de cor (copiar isto primeiro)

O Razy usa Tailwind com cores semânticas mapeadas em variáveis CSS. O tema
**escuro é o padrão** (`:root`); o claro entra com a classe `.light` no
`<html>` (o `GraficoAnalista` observa essa classe com `MutationObserver` e
redesenha).

### `assets/css/tailwind.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html, body, #__nuxt { height: 100%; }

  /* Tema escuro (padrão) */
  :root {
    --color-background: 20 21 24;
    --color-foreground: 255 255 255;
    --color-primary: 59 130 246;
    --color-primary-fg: 255 255 255;
    --color-secondary: 26 27 31;
    --color-secondary-fg: 255 255 255;
    --color-accent: 30 41 73;
    --color-accent-fg: 255 255 255;
    --color-muted: 38 39 43;
    --color-muted-fg: 160 163 172;
    --color-card: 26 27 31;
    --color-card-fg: 255 255 255;
    --color-popover: 26 27 31;
    --color-popover-fg: 255 255 255;
    --color-destructive: 239 68 68;
    --color-destructive-fg: 255 255 255;
    --color-destructive-surface: 47 31 31;
    --color-border: 38 39 43;
    --color-input: 38 39 43;
    --color-ring: 59 130 246;
  }

  /* Tema claro */
  .light {
    --color-background: 248 249 250;
    --color-foreground: 17 24 39;
    --color-primary: 59 130 246;
    --color-primary-fg: 255 255 255;
    --color-secondary: 255 255 255;
    --color-secondary-fg: 17 24 39;
    --color-accent: 219 234 254;
    --color-accent-fg: 30 58 138;
    --color-muted: 243 244 246;
    --color-muted-fg: 107 114 128;
    --color-card: 255 255 255;
    --color-card-fg: 17 24 39;
    --color-popover: 255 255 255;
    --color-popover-fg: 17 24 39;
    --color-destructive: 239 68 68;
    --color-destructive-fg: 255 255 255;
    --color-destructive-surface: 254 242 242;
    --color-border: 229 231 235;
    --color-input: 229 231 235;
    --color-ring: 59 130 246;
  }
}
```

### `tailwind.config.ts` (trecho `colors`)

```ts
import type { Config } from 'tailwindcss'

const config: Partial<Config> = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'rgb(var(--color-background) / <alpha-value>)',
        foreground: 'rgb(var(--color-foreground) / <alpha-value>)',
        primary:   { DEFAULT: 'rgb(var(--color-primary) / <alpha-value>)',   foreground: 'rgb(var(--color-primary-fg) / <alpha-value>)' },
        secondary: { DEFAULT: 'rgb(var(--color-secondary) / <alpha-value>)', foreground: 'rgb(var(--color-secondary-fg) / <alpha-value>)' },
        accent:    { DEFAULT: 'rgb(var(--color-accent) / <alpha-value>)',    foreground: 'rgb(var(--color-accent-fg) / <alpha-value>)' },
        muted:     { DEFAULT: 'rgb(var(--color-muted) / <alpha-value>)',     foreground: 'rgb(var(--color-muted-fg) / <alpha-value>)' },
        card:      { DEFAULT: 'rgb(var(--color-card) / <alpha-value>)',      foreground: 'rgb(var(--color-card-fg) / <alpha-value>)' },
        popover:   { DEFAULT: 'rgb(var(--color-popover) / <alpha-value>)',   foreground: 'rgb(var(--color-popover-fg) / <alpha-value>)' },
        destructive: { DEFAULT: 'rgb(var(--color-destructive) / <alpha-value>)', foreground: 'rgb(var(--color-destructive-fg) / <alpha-value>)' },
        destructiveSurface: 'rgb(var(--color-destructive-surface) / <alpha-value>)',
        border: 'rgb(var(--color-border) / <alpha-value>)',
        input:  'rgb(var(--color-input) / <alpha-value>)',
        ring:   'rgb(var(--color-ring) / <alpha-value>)',
        white: '#FFFFFF'
      }
    }
  }
}
export default config
```

### Se o outro app NÃO tiver essas classes semânticas

Troque pelo hex equivalente (tema escuro, que é o padrão):

| Classe | Papel | Hex escuro | Hex claro |
|---|---|---|---|
| `bg-background` | fundo da página / campos | `#141518` | `#F8F9FA` |
| `bg-card` | fundo do painel | `#1A1B1F` | `#FFFFFF` |
| `bg-muted` / `hover:bg-muted` | fundo sutil, hover | `#26272B` | `#F3F4F6` |
| `text-foreground` | texto principal | `#FFFFFF` | `#111827` |
| `text-muted-foreground` | texto secundário / rótulo | `#A0A3AC` | `#6B7280` |
| `border-border` | borda padrão | `#26272B` | `#E5E7EB` |
| `bg-primary` / `text-primary` | cor de marca (ação, azul) | `#3B82F6` | `#3B82F6` |
| `text-primary-foreground` | texto sobre primary | `#FFFFFF` | `#FFFFFF` |
| `text-destructive` | vermelho de erro | `#EF4444` | `#EF4444` |

As cores **temáticas dos cards** (blue/violet/emerald/amber/rose/indigo) são
as escalas padrão do Tailwind — não dependem das variáveis acima, funcionam
igual em qualquer projeto Tailwind.

---

## 3. Sistema de cores semânticas (a regra que rege tudo)

**A cor não é decoração — ela diz o que a coisa significa.** A mesma paleta se
repete da pergunta (catálogo) até a resposta (card) até o gráfico.

| Tom | Tailwind base | Significado | Onde aparece |
|---|---|---|---|
| **azul** | `blue-500` | fato neutro, visão geral, próxima ação | card `visao_geral`, `proxima_acao`; grupo "Sobre um cliente" |
| **roxo** | `violet-500` | narrativa, o que aconteceu | card `resumo` |
| **verde** | `emerald-500` | julgamento positivo (boa chance, sem problema) | card `interesse` nível alta, `atencao` nível baixa; grupo "Sobre um vendedor"; tile "bom" |
| **amarelo** | `amber-500` | precisa de atenção, pendência, ambíguo | card `atencao` nível média, `interesse` nível média, `esclarecer`; grupo "Sobre o funil"; tile "atenção"; faixa de cobertura |
| **vermelho** | `rose-500` | julgamento negativo / grave | card `interesse` nível baixa, `atencao` nível alta; tile "ruim" |
| **cinza** | `border`/`muted` | dado secundário | card `coletado` |
| **índigo** | `indigo-500` | (só no catálogo) grupo "Sobre os SDRs" | — |

Regra de ouro do tile: **a cor sai do VALOR, não do rótulo.** "Conversas
ativas" é escala (nem bom nem ruim) → sempre neutro. "Resposta média" fica
verde/amarelo/vermelho conforme os minutos.

### Regra crítica do Tailwind (classes por extenso)

O Tailwind varre o código-fonte como **texto**. Classe montada em runtime
(`'border-' + cor`, `.replace('text-','bg-')`) **não é gerada** e some no
build. Por isso os mapas de tom abaixo têm as classes escritas inteiras.

> Exceção usada de propósito no `CardAnalista`: `estilo.icone.replace('text-', 'bg-')`
> para o bullet da lista — funciona só porque `text-blue-500`, `bg-blue-500`
> etc. já aparecem escritos em outro lugar do mesmo arquivo (no mapa `TONS`).
> Se copiar isso, garanta que as duas variantes existam no source.

---

## 4. A bolha (FAB)

```html
<button
  v-show="!aberto"
  @click="abrir"
  class="fixed right-6 z-40 w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/40 flex items-center justify-center hover:-translate-y-0.5 hover:scale-105 transition-transform focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background"
  :class="conversaAtiva ? 'bottom-44' : 'bottom-6'"
  title="Analista de Atendimento"
  aria-label="Abrir o Analista de Atendimento"
>
  <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /><path d="M8.5 11.5l2 2 4-4.5" />
  </svg>
</button>
```

`bottom-6` normal; `bottom-44` quando há uma conversa aberta (o composer de
Conversas ocupa esse canto). O ícone é uma lupa com um "check" dentro.

---

## 5. Véu + painel lateral (transições)

```html
<!-- Véu -->
<transition
  enter-active-class="transition-opacity duration-200" leave-active-class="transition-opacity duration-200"
  enter-from-class="opacity-0" leave-to-class="opacity-0"
>
  <div v-if="aberto" @click="fechar" class="fixed inset-0 z-40 bg-black/40" />
</transition>

<!-- Painel -->
<transition
  enter-active-class="transition-transform duration-300 ease-out" leave-active-class="transition-transform duration-200 ease-in"
  enter-from-class="translate-x-full" leave-to-class="translate-x-full"
>
  <aside
    v-if="aberto"
    class="fixed top-0 right-0 bottom-0 z-50 bg-card border-l border-border flex flex-col shadow-2xl w-full"
    :class="ampliado ? 'sm:w-[min(980px,100vw)]' : 'sm:w-[min(700px,100vw)]'"
    role="dialog" aria-label="Analista de Atendimento"
  >
    <!-- header / corpo / footer -->
  </aside>
</transition>
```

`Escape` fecha o painel (listener global). O corpo é
`flex-1 overflow-y-auto px-4 py-4 space-y-4`.

### Cabeçalho

```html
<header class="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0">
  <div class="w-8 h-8 rounded-lg bg-primary text-primary-foreground grid place-items-center shrink-0">
    <svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /><path d="M8.5 11.5l2 2 4-4.5" />
    </svg>
  </div>
  <div class="min-w-0">
    <p class="text-sm font-bold text-foreground leading-tight">Analista de Atendimento</p>
    <p class="text-[11px] text-muted-foreground flex items-center gap-1.5">
      <span v-if="resumo?.ativas != null" class="w-1.5 h-1.5 rounded-full bg-emerald-500" />
      {{ resumo?.ativas != null ? `Lendo ${resumo.ativas} conversas` : 'Pergunte sobre os atendimentos' }}
    </p>
  </div>
  <div class="ml-auto flex items-center gap-0.5">
    <!-- ampliar (só sm+): w-8 h-8 rounded-lg place-items-center text-muted-foreground hover:text-foreground hover:bg-muted -->
    <!-- nova conversa (v-if="temConversa"): mesmo estilo -->
    <!-- fechar: mesmo estilo -->
  </div>
</header>
```

Ícones dos botões do cabeçalho (SVG, `w-4 h-4`, `stroke-width="2"`):
- Ampliar: `M15 3h6v6M21 3l-7 7M9 21H3v-6M3 21l7-7` — Reduzir: `M14 10h6M20 10l-7-7M10 14H4M4 14l7 7`
- Nova conversa: `M3 12a9 9 0 1 0 2.6-6.4` + `M3 3v5h5`
- Fechar: `M18 6L6 18M6 6l12 12`

### Rodapé (input)

```html
<footer class="border-t border-border px-3 py-3 shrink-0 space-y-2">
  <div class="flex items-center gap-2 bg-background border border-border rounded-xl px-3 py-2 focus-within:border-primary transition">
    <input
      ref="inputRef" v-model="entrada" @keydown.enter="enviar()" :disabled="pensando"
      type="text" placeholder="Pergunte sobre um cliente, vendedor ou período..."
      class="flex-1 min-w-0 bg-transparent border-0 outline-none text-foreground text-[13.5px] placeholder:text-muted-foreground disabled:opacity-60"
    />
    <button
      @click="enviar()" :disabled="pensando || !entrada.trim()"
      class="w-8 h-8 rounded-lg bg-primary text-primary-foreground grid place-items-center shrink-0 disabled:opacity-40 transition"
      aria-label="Enviar"
    >
      <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 12h15M13 6l6 6-6 6" />
      </svg>
    </button>
  </div>
  <p class="text-[10.5px] text-muted-foreground text-center">
    Responde com base nas mensagens gravadas. Sempre mostra o que leu.
  </p>
</footer>
```

### "Consultando..." (loading)

```html
<div v-if="pensando" class="flex items-center gap-2.5 text-[12.5px] text-muted-foreground">
  <svg class="w-3.5 h-3.5 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
    <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
  </svg>
  Consultando os atendimentos...
</div>
```

Esse spinner (círculo `opacity-25` + arco `opacity-75` girando) é o
"vocabulário visual" reaproveitado em todos os botões de carregamento.

---

## 6. Tela de abertura — os cards iniciais

Mostrada enquanto `turnos.length === 0`. Ordem dos blocos:

### 6.1 Título

```html
<div>
  <p class="text-[15px] font-semibold text-foreground">O que você quer saber?</p>
  <p class="text-[13px] text-muted-foreground mt-1">Clique numa pergunta ou escreva a sua.</p>
</div>
```

### 6.2 Card de contexto (só quando há conversa aberta na tela)

```html
<div v-if="conversaAtiva" class="flex items-center gap-2.5 rounded-xl border border-primary/30 bg-primary/5 px-3 py-2.5">
  <div class="w-8 h-8 rounded-full bg-primary/15 text-primary grid place-items-center text-[11px] font-bold shrink-0">
    {{ (conversaAtiva.nome || '?').slice(0, 2).toUpperCase() }}
  </div>
  <div class="min-w-0 flex-1">
    <p class="text-[13px] font-semibold text-foreground truncate">
      {{ conversaAtiva.nome || formatarTelefoneBR(conversaAtiva.numero) }}
    </p>
    <p class="text-[11.5px] text-muted-foreground truncate">
      {{ formatarTelefoneBR(conversaAtiva.numero) }}<template v-if="conversaAtiva.vendedor"> · {{ conversaAtiva.vendedor }}</template>
    </p>
  </div>
  <span class="text-[10px] font-bold uppercase tracking-wide text-primary bg-primary/10 px-2 py-1 rounded shrink-0">Aberta</span>
</div>
```

### 6.3 Os 4 tiles de números (do `/resumo`)

```html
<div v-if="tiles.length" class="grid grid-cols-2 sm:grid-cols-4 gap-2">
  <div v-for="(t, i) in tiles" :key="i" class="rounded-xl border px-3 py-2.5" :class="TILE_CLASSES[t.tom].caixa">
    <p class="text-xl font-bold tabular-nums leading-tight" :class="TILE_CLASSES[t.tom].numero">{{ t.valor }}</p>
    <p class="text-[11px] text-muted-foreground leading-tight">{{ t.rotulo }}</p>
  </div>
</div>
```

```ts
type TomTile = 'neutro' | 'bom' | 'atencao' | 'ruim'

const TILE_CLASSES: Record<TomTile, { caixa: string; numero: string }> = {
  neutro:  { caixa: 'border-border bg-background',                 numero: 'text-foreground' },
  bom:     { caixa: 'border-emerald-500/25 bg-emerald-500/[0.07]', numero: 'text-emerald-600 dark:text-emerald-400' },
  atencao: { caixa: 'border-amber-500/30 bg-amber-500/[0.08]',     numero: 'text-amber-600 dark:text-amber-400' },
  ruim:    { caixa: 'border-rose-500/25 bg-rose-500/[0.07]',       numero: 'text-rose-600 dark:text-rose-400' }
}

// Os 4 tiles, do resumo da operação:
const tiles = computed(() => {
  const r = resumo.value
  if (!r) return []
  const paradas = r.paradas_3d ?? null
  const resp    = r.resposta_media_min ?? null

  const tomParadas: TomTile =
    paradas == null ? 'neutro' : paradas === 0 ? 'bom' : paradas > 5 ? 'ruim' : 'atencao'
  // até 1h bom, até 2h atenção, acima disso o cliente já desistiu de esperar
  const tomResposta: TomTile =
    resp == null ? 'neutro' : resp <= 60 ? 'bom' : resp <= 120 ? 'atencao' : 'ruim'

  return [
    { valor: r.ativas ?? '—',        rotulo: 'conversas ativas',   tom: 'neutro' },
    { valor: r.movimento_24h ?? '—', rotulo: 'com movimento hoje', tom: r.movimento_24h ? 'bom' : 'neutro' },
    { valor: paradas ?? '—',         rotulo: 'paradas +3 dias',    tom: tomParadas },
    { valor: formatarMin(resp),      rotulo: 'resposta média',     tom: tomResposta }
  ]
})

function formatarMin(min: number | null | undefined): string {
  if (min == null) return '—'
  if (min < 60) return `${Math.round(min)} min`
  const h = Math.floor(min / 60)
  return `${h}h ${Math.round(min % 60)}min`
}
```

### 6.4 Faixa de cobertura (só quando há mensagem ilegível)

```html
<div v-if="coberturaResumo" class="flex gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2.5">
  <svg class="w-4 h-4 text-amber-500 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
  </svg>
  <div class="min-w-0">
    <p class="text-[12.5px] font-bold text-amber-600 dark:text-amber-400 leading-snug">
      Consigo ler {{ coberturaResumo.pct }}% do histórico
    </p>
    <p class="text-[12px] text-muted-foreground mt-0.5">
      {{ coberturaResumo.sem }} mensagens são áudio sem transcrição ou imagem sem legenda.
    </p>
  </div>
</div>
```

```ts
const coberturaResumo = computed(() => {
  const r = resumo.value
  if (!r || !r.total_msgs || !r.msgs_sem_texto) return null
  return { pct: r.cobertura_pct ?? 0, sem: r.msgs_sem_texto, total: r.total_msgs }
})
```

### 6.5 O CATÁLOGO de perguntas (4 grupos)

```html
<div class="space-y-3.5">
  <div v-for="g in CATALOGO" :key="g.titulo" class="space-y-1.5">
    <p class="text-xs font-bold flex items-center gap-2" :class="grupoClasses(g.icone).titulo">
      <svg class="w-3.5 h-3.5 shrink-0" :class="grupoClasses(g.icone).icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <template v-if="g.icone === 'user'"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></template>
        <template v-else-if="g.icone === 'chart'"><path d="M3 3v18h18" /><path d="M7 14l4-4 3 3 5-6" /></template>
        <template v-else-if="g.icone === 'sdr'"><path d="M3 18v-6a9 9 0 0 1 18 0v6" /><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" /></template>
        <template v-else><path d="M3 4h18l-7 8v7l-4 2v-9z" /></template>
      </svg>
      {{ g.titulo }}
    </p>
    <div class="grid sm:grid-cols-2 gap-1.5">
      <button
        v-for="p in g.perguntas" :key="p" @click="enviar(p)"
        class="text-left text-[12.5px] leading-snug px-3 py-2.5 rounded-lg border transition"
        :class="grupoClasses(g.icone).botao"
      >{{ p }}</button>
    </div>
  </div>
</div>
```

```ts
// Cor de cada grupo = cor do card que aquela pergunta produz. Repouso quase
// neutro (só título + ícone com cor); a caixa do botão acende no hover.
const GRUPO_CLASSES: Record<string, { titulo: string; icone: string; botao: string }> = {
  user: {
    titulo: 'text-blue-600 dark:text-blue-400',
    icone:  'text-blue-500',
    botao:  'border-blue-500/20 bg-blue-500/[0.04] hover:border-blue-500/50 hover:bg-blue-500/[0.09]'
  },
  chart: {
    titulo: 'text-emerald-600 dark:text-emerald-400',
    icone:  'text-emerald-500',
    botao:  'border-emerald-500/20 bg-emerald-500/[0.04] hover:border-emerald-500/50 hover:bg-emerald-500/[0.09]'
  },
  sdr: {
    titulo: 'text-indigo-600 dark:text-indigo-400',
    icone:  'text-indigo-500',
    botao:  'border-indigo-500/20 bg-indigo-500/[0.04] hover:border-indigo-500/50 hover:bg-indigo-500/[0.09]'
  },
  funnel: {
    titulo: 'text-amber-600 dark:text-amber-400',
    icone:  'text-amber-500',
    botao:  'border-amber-500/25 bg-amber-500/[0.05] hover:border-amber-500/50 hover:bg-amber-500/[0.10]'
  }
}
const GRUPO_NEUTRO = {
  titulo: 'text-foreground',
  icone:  'text-muted-foreground',
  botao:  'border-border bg-background hover:border-primary hover:bg-primary/5'
}
const grupoClasses = (icone: string) => GRUPO_CLASSES[icone] || GRUPO_NEUTRO
```

---

## 7. As perguntas (catálogo completo, texto exato)

O **primeiro grupo é contextual**. Com uma conversa aberta atrás do painel,
ele fala do cliente daquela conversa (telefone já formatado); sem conversa
aberta, não inventa telefone — oferece o caminho de buscar.

### Grupo 1a — COM conversa aberta · `icone: 'user'` (azul)
Título: **`Sobre {nome do contato ou telefone}`**
- `Como está o atendimento do telefone {tel}?`
- `Na conversa do telefone {tel}, o que ficou sem resposta?`
- `O cliente do telefone {tel} tem chance de fechar?`
- `Resuma a conversa do telefone {tel}`

### Grupo 1b — SEM conversa aberta · `icone: 'user'` (azul)
Título: **Sobre um cliente**
- `Abra uma conversa para eu analisar aquele cliente` *(não é pergunta — ver abaixo)*
- `Quais clientes estão sem retorno há mais tempo?`

### Grupo 2 — `icone: 'chart'` (verde/emerald)
Título: **Sobre um vendedor**
- `Analise o desempenho de cada vendedor`
- `Quais vendedores estão sem movimento hoje?`

### Grupo 3 — `icone: 'sdr'` (índigo)
Título: **Sobre os SDRs**
- `Analise o desempenho de cada SDR`
- `Quantos atendimentos os SDRs têm aberto no total?`
- `Quais SDRs estão sem movimento hoje?`

### Grupo 4 — `icone: 'funnel'` (amarelo/amber)
Título: **Sobre o funil**
- `Quais conversas estão paradas há mais de 3 dias?`
- `Onde estou perdendo cliente?`

### A "dica" que não é pergunta

```ts
const DICA_ABRIR_CONVERSA = 'Abra uma conversa para eu analisar aquele cliente'

async function enviar(texto?: string) {
  const p = (texto ?? entrada.value).trim()
  if (!p || pensando.value) return
  // Dica: prepara o campo em vez de mandar pro LLM.
  if (p === DICA_ABRIR_CONVERSA) {
    entrada.value = 'Como está o atendimento do telefone '
    inputRef.value?.focus()
    return
  }
  entrada.value = ''
  await perguntar(p)
}
```

### Código do catálogo (computed)

```ts
const CATALOGO = computed<{ titulo: string; icone: string; perguntas: string[] }[]>(() => {
  const c = conversaAtiva.value
  const tel = c ? formatarTelefoneBR(c.numero) : ''
  const cliente = c
    ? {
        titulo: `Sobre ${c.nome || tel}`,
        icone: 'user',
        perguntas: [
          `Como está o atendimento do telefone ${tel}?`,
          `Na conversa do telefone ${tel}, o que ficou sem resposta?`,
          `O cliente do telefone ${tel} tem chance de fechar?`,
          `Resuma a conversa do telefone ${tel}`
        ]
      }
    : {
        titulo: 'Sobre um cliente',
        icone: 'user',
        perguntas: [
          'Abra uma conversa para eu analisar aquele cliente',
          'Quais clientes estão sem retorno há mais tempo?'
        ]
      }

  return [
    cliente,
    { titulo: 'Sobre um vendedor', icone: 'chart', perguntas: [
      'Analise o desempenho de cada vendedor',
      'Quais vendedores estão sem movimento hoje?'
    ]},
    { titulo: 'Sobre os SDRs', icone: 'sdr', perguntas: [
      'Analise o desempenho de cada SDR',
      'Quantos atendimentos os SDRs têm aberto no total?',
      'Quais SDRs estão sem movimento hoje?'
    ]},
    { titulo: 'Sobre o funil', icone: 'funnel', perguntas: [
      'Quais conversas estão paradas há mais de 3 dias?',
      'Onde estou perdendo cliente?'
    ]}
  ]
})
```

---

## 8. Turno de conversa (pergunta + resposta)

```html
<template v-for="(t, i) in turnos" :key="t.id">
  <!-- pergunta do usuário: balão à direita -->
  <div v-if="t.papel === 'user'" :data-turno="t.id" class="flex justify-end">
    <p class="max-w-[85%] bg-primary text-primary-foreground text-[13.5px] px-3.5 py-2 rounded-2xl rounded-br-sm">{{ t.texto }}</p>
  </div>

  <!-- resposta -->
  <div v-else :data-turno="t.id" class="space-y-3">
    <!-- faixa de cobertura do turno (ver 8.1) -->
    <!-- cards (ver seção 9) OU markdown de reserva (ver 8.2) -->
    <div v-if="!t.erro && t.cards?.length" class="space-y-2.5">
      <CardAnalista v-for="(c, n) in t.cards" :key="n" :card="c" @escolher="enviar" />
    </div>
    <div v-else class="analista-md text-[13.5px] leading-relaxed"
         :class="t.erro ? 'text-destructive' : 'text-foreground'"
         v-html="renderizar(t.texto)" />

    <!-- gráficos: depois do texto (confirmam a conclusão) -->
    <div v-if="t.graficos?.length" class="grid gap-2.5"
         :class="ampliado && t.graficos.length > 1 ? 'sm:grid-cols-2' : 'grid-cols-1'">
      <GraficoAnalista v-for="(g, n) in t.graficos" :key="n" :spec="g" />
    </div>

    <!-- botão exportar (ver seção 11) -->
  </div>
</template>
```

**Rolagem:** pergunta recém-enviada → rola pro fim (mostra o que a pessoa
escreveu + "consultando..."). Resposta que chegou → sobe e ancora o **começo**
da pergunta que a gerou no topo da área de leitura (`getBoundingClientRect`),
porque a resposta vem em vários cards e o dono podia achar que o último era
tudo. Marcador: `[data-turno="{id}"]`.

### 8.1 Faixa de cobertura do turno

```html
<div v-if="t.cobertura && t.cobertura.sem_conteudo > 0" class="flex gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2.5">
  <svg class="w-4 h-4 text-amber-500 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
  </svg>
  <div class="min-w-0 flex-1">
    <p class="text-[12.5px] font-bold text-amber-600 dark:text-amber-400 leading-snug">
      Li {{ t.cobertura.lidas }} de {{ t.cobertura.total }} mensagens
    </p>
    <p class="text-[12px] text-muted-foreground mt-0.5">
      {{ t.cobertura.sem_conteudo }} sem conteúdo legível (áudio sem transcrição ou imagem sem legenda).
    </p>
    <div class="h-1 rounded-full bg-muted overflow-hidden mt-2">
      <div class="h-full bg-amber-500 rounded-full" :style="{ width: Math.round((t.cobertura.lidas / t.cobertura.total) * 100) + '%' }" />
    </div>
  </div>
</div>
```

### 8.2 Renderer markdown de reserva + CSS scoped

Usado quando a resposta vem com `erro` ou o ai-service ainda não manda `cards`.
Escapa HTML **antes** do markdown (o texto foi gerado por LLM que leu mensagens
de terceiros). Suporta `**negrito**`, `*itálico*`, `` `code` ``, `#` títulos,
listas `- / 1.` e tabelas `| a | b |`.

```css
/* <style scoped> — `:deep` porque o HTML entra via v-html */
.analista-md :deep(p) { margin: 0 0 0.6rem; }
.analista-md :deep(p:last-child) { margin-bottom: 0; }
.analista-md :deep(h4) { font-size: 13.5px; font-weight: 700; margin: 1rem 0 0.4rem; }
.analista-md :deep(h4:first-child) { margin-top: 0; }
.analista-md :deep(ul) { margin: 0 0 0.6rem; padding-left: 1.1rem; list-style: disc; }
.analista-md :deep(li) { margin-bottom: 0.25rem; }
.analista-md :deep(strong) { font-weight: 600; }
.analista-md :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.88em;
  background: rgb(var(--color-muted));
  padding: 0.1em 0.35em;
  border-radius: 4px;
}
.analista-md :deep(.tabela-scroll) {
  overflow-x: auto;
  border: 1px solid rgb(var(--color-border));
  border-radius: 10px;
  margin: 0 0 0.7rem;
}
.analista-md :deep(table) { border-collapse: collapse; width: 100%; font-size: 12.5px; }
.analista-md :deep(th) {
  text-align: left;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgb(var(--color-muted-fg));
  background: rgb(var(--color-muted));
  padding: 0.55rem 0.7rem;
  white-space: nowrap;
}
.analista-md :deep(td) {
  padding: 0.55rem 0.7rem;
  border-top: 1px solid rgb(var(--color-border));
  font-variant-numeric: tabular-nums;
}
```

```ts
function renderizar(md: string): string {
  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  const linhas = esc(md || '').split('\n')
  const out: string[] = []
  let lista = false
  let tabela = false

  const fecharLista  = () => { if (lista)  { out.push('</ul>'); lista = false } }
  const fecharTabela = () => { if (tabela) { out.push('</tbody></table></div>'); tabela = false } }

  const inline = (s: string) =>
    s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
     .replace(/(^|[\s(])\*([^*]+?)\*(?=[\s.,;:)]|$)/g, '$1<em>$2</em>')
     .replace(/`(.+?)`/g, '<code>$1</code>')

  for (let i = 0; i < linhas.length; i++) {
    const t = (linhas[i] || '').trim()
    if (!t) { fecharLista(); fecharTabela(); continue }

    const proxima = (linhas[i + 1] || '').trim()
    if (t.startsWith('|') && /^\|[\s:|-]+\|$/.test(proxima)) {
      fecharLista(); fecharTabela()
      const celulas = (l: string) => l.replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
      out.push('<div class="tabela-scroll"><table><thead><tr>')
      for (const c of celulas(t)) out.push(`<th>${inline(c)}</th>`)
      out.push('</tr></thead><tbody>')
      tabela = true; i++; continue
    }
    if (tabela && t.startsWith('|')) {
      const celulas = t.replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
      out.push('<tr>' + celulas.map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>')
      continue
    }
    fecharTabela()

    if (/^#{1,6}\s/.test(t)) { fecharLista(); out.push(`<h4>${inline(t.replace(/^#+\s*/, ''))}</h4>`); continue }
    if (/^[-*+]\s+/.test(t) || /^\d+\.\s+/.test(t)) {
      if (!lista) { out.push('<ul>'); lista = true }
      out.push(`<li>${inline(t.replace(/^([-*+]|\d+\.)\s+/, ''))}</li>`); continue
    }
    fecharLista()
    out.push(`<p>${inline(t)}</p>`)
  }
  fecharLista(); fecharTabela()
  return out.join('')
}
```

---

## 9. Os cards temáticos da resposta — `CardAnalista.vue`

**A cor sai do `tipo` + `nivel` que vieram do backend**, nunca de escolha do
componente. Fundos translúcidos (`/[0.07]`, `/[0.08]`) para o mesmo card
funcionar sobre claro e escuro sem duas paletas.

### 9.1 Tipos de card

| `tipo` | Tom | Título padrão | Quando aparece |
|---|---|---|---|
| `visao_geral` | azul | "Visão geral" | montado **por código** (ver 9.5); sempre que há uma conversa identificada |
| `resumo` | roxo | "Resumo da conversa" (+ nome do cliente) | o que aconteceu, em ordem cronológica, itens curtos |
| `coletado` | cinza | "Informações coletadas" | dados que o cliente forneceu (produto, necessidade, faixa de preço, CNPJ, preferências) — só se ele realmente informou |
| `interesse` | verde/amarelo/vermelho (por `nivel`) | "Interesse e chance de fechamento" | sinais de interesse tirados das mensagens |
| `atencao` | vermelho/amarelo/verde (por `nivel`) | "Pontos de atenção" | demora, pergunta ignorada, sem follow-up, orçamento não enviado, cliente esperando, conversa parada |
| `proxima_acao` | azul | "Próxima ação recomendada" | uma recomendação concreta, em `texto` |
| `esclarecer` | amarelo | (texto livre) | só quando as leituras possíveis levam a respostas diferentes; `itens` são reformulações clicáveis |

### 9.2 Mapa de tons (classes por extenso — não montar em runtime)

```ts
type Tom = 'azul' | 'roxo' | 'verde' | 'amarelo' | 'vermelho' | 'cinza'

const TONS: Record<Tom, { borda: string; fundo: string; titulo: string; icone: string; anel: string }> = {
  azul:     { borda: 'border-blue-500/25',    fundo: 'bg-blue-500/[0.07]',    titulo: 'text-blue-600 dark:text-blue-400',       icone: 'text-blue-500',    anel: 'ring-blue-500/30' },
  roxo:     { borda: 'border-violet-500/25',  fundo: 'bg-violet-500/[0.07]',  titulo: 'text-violet-600 dark:text-violet-400',   icone: 'text-violet-500',  anel: 'ring-violet-500/30' },
  verde:    { borda: 'border-emerald-500/25', fundo: 'bg-emerald-500/[0.07]', titulo: 'text-emerald-600 dark:text-emerald-400', icone: 'text-emerald-500', anel: 'ring-emerald-500/30' },
  amarelo:  { borda: 'border-amber-500/30',   fundo: 'bg-amber-500/[0.08]',   titulo: 'text-amber-600 dark:text-amber-400',     icone: 'text-amber-500',   anel: 'ring-amber-500/30' },
  vermelho: { borda: 'border-rose-500/25',    fundo: 'bg-rose-500/[0.07]',    titulo: 'text-rose-600 dark:text-rose-400',       icone: 'text-rose-500',    anel: 'ring-rose-500/30' },
  cinza:    { borda: 'border-border',         fundo: 'bg-muted/40',           titulo: 'text-foreground',                        icone: 'text-muted-foreground', anel: 'ring-border' }
}

const tom = computed<Tom>(() => {
  const { tipo, nivel } = props.card
  if (tipo === 'visao_geral')  return 'azul'
  if (tipo === 'resumo')       return 'roxo'
  if (tipo === 'coletado')     return 'cinza'
  if (tipo === 'proxima_acao') return 'azul'
  if (tipo === 'esclarecer')   return 'amarelo'
  if (tipo === 'interesse') return nivel === 'alta' ? 'verde' : nivel === 'baixa' ? 'vermelho' : 'amarelo'
  if (tipo === 'atencao')   return nivel === 'alta' ? 'vermelho' : nivel === 'baixa' ? 'verde' : 'amarelo'
  return 'cinza'
})
```

### 9.3 Badge (etiqueta de nível — só onde carrega julgamento)

```ts
const badge = computed(() => {
  const { tipo, nivel } = props.card
  if (!nivel) return null
  if (tipo === 'interesse') return { texto: `Chance ${nivel === 'media' ? 'média' : nivel}`, tom: tom.value }
  if (tipo === 'atencao' && nivel !== 'baixa') return { texto: nivel === 'alta' ? 'Requer ação' : 'Pendência', tom: tom.value }
  return null
})
```

### 9.4 Template completo do card

```html
<template>
  <section class="rounded-xl border px-4 py-3.5" :class="[estilo.borda, estilo.fundo]">
    <header class="flex items-center gap-2 mb-2.5">
      <svg class="w-4 h-4 shrink-0" :class="estilo.icone" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <template v-if="card.tipo === 'visao_geral'"><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18M9 10v10" /></template>
        <template v-else-if="card.tipo === 'resumo'"><path d="M4 6h16M4 12h16M4 18h10" /></template>
        <template v-else-if="card.tipo === 'coletado'"><path d="M20 7h-9M14 17H5" /><circle cx="17" cy="17" r="3" /><circle cx="7" cy="7" r="3" /></template>
        <template v-else-if="card.tipo === 'interesse'"><path d="M3 3v18h18" /><path d="M7 14l4-4 3 3 5-6" /></template>
        <template v-else-if="card.tipo === 'esclarecer'"><circle cx="12" cy="12" r="10" /><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01" /></template>
        <template v-else-if="card.tipo === 'atencao'"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></template>
        <template v-else><path d="M5 12h14M13 6l6 6-6 6" /></template>
      </svg>

      <h4 class="text-[12.5px] font-bold tracking-tight" :class="estilo.titulo">{{ card.titulo }}</h4>

      <span v-if="badge"
        class="ml-auto text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded shrink-0"
        :class="[TONS[badge.tom].fundo, TONS[badge.tom].titulo, 'ring-1', TONS[badge.tom].anel]"
      >{{ badge.texto }}</span>
    </header>

    <!-- Pares rótulo/valor: visão geral e dados coletados -->
    <dl v-if="card.campos?.length" class="grid grid-cols-2 gap-x-4 gap-y-2 m-0">
      <div v-for="(c, i) in card.campos" :key="i" class="min-w-0">
        <dt class="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{{ c.rotulo }}</dt>
        <dd class="text-[12.5px] text-foreground m-0 break-words">{{ c.valor }}</dd>
      </div>
    </dl>

    <!-- Esclarecer: cada item é uma pergunta clicável → vira botão -->
    <ul v-if="card.tipo === 'esclarecer' && card.itens?.length" class="space-y-1.5 m-0 p-0 list-none" :class="card.campos?.length ? 'mt-3' : ''">
      <li v-for="(t, i) in card.itens" :key="i">
        <button type="button" @click="emit('escolher', t)"
          class="w-full text-left text-[12.5px] leading-snug text-foreground bg-amber-500/[0.06] border border-amber-500/25 rounded-lg px-3 py-2 hover:bg-amber-500/[0.12] hover:border-amber-500/50 transition focus:outline-none focus:ring-2 focus:ring-amber-500/50"
        >{{ t }}</button>
      </li>
    </ul>

    <!-- Itens normais: bullet colorido com o tom do card -->
    <ul v-else-if="card.itens?.length" class="space-y-1.5 m-0 p-0 list-none" :class="card.campos?.length ? 'mt-3' : ''">
      <li v-for="(t, i) in card.itens" :key="i" class="flex gap-2 text-[12.5px] text-foreground leading-snug">
        <span class="shrink-0 mt-[7px] w-1 h-1 rounded-full" :class="estilo.icone.replace('text-', 'bg-')" />
        <span class="min-w-0">{{ t }}</span>
      </li>
    </ul>

    <p v-if="card.texto" class="text-[12.5px] text-foreground leading-relaxed m-0" :class="(card.itens?.length || card.campos?.length) ? 'mt-3' : ''">
      {{ card.texto }}
    </p>
  </section>
</template>
```

`@escolher` emite a pergunta reformulada (card `esclarecer`) — o painel a
reenvia via `enviar(pergunta)`.

### 9.5 Card `visao_geral` — montado 100% por código (backend)

Nome, telefone, atendente, datas e contagem são **fato puro** — o tipo de
campo que um LLM troca/arredonda sem querer. Por isso o prompt **proíbe** o
modelo de produzir este card. Campos (pares rótulo/valor, exibidos no `<dl>`):

| Rótulo | Valor |
|---|---|
| Cliente | `nome_contato` ou "sem nome" |
| Telefone | máscara BR `(14) 98138-6372` |
| Atendente | nome do vendedor, ou "Nenhum profissional (atendido pelo canal)" p/ SDR, ou "sem atendente atribuído" |
| Canal / número | `{nome da instância} · {telefone do canal}` |
| Primeiro contato | data BR (fuso America/Sao_Paulo) de `opened_at`/`created_at` |
| Cliente falou por último | `{data} ({há quanto tempo})` ou "—" |
| Atendente respondeu | `{data} ({há quanto tempo})` ou "ainda não respondeu" |
| Mensagens | total (da timeline lida, ou `total_msgs`) |
| Sem interação há | `sem_interacao_ha` (ex.: "2d 4h") |
| Status | Aberto / Em atendimento / Resolvido / Arquivado — sufixo "· cliente aguardando" |

Ícone: `<rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18M9 10v10" />`.

---

## 10. Gráficos — `GraficoAnalista.vue`

`chart.js@^4.5`. Os **dados vêm prontos do backend**, derivados do retorno
real das consultas — o LLM não escolhe número nem rótulo. Tipos:
`'barras' | 'barras_h' | 'rosca'`.

### 10.1 Duas paletas: séries (fixa) × moldura (segue o tema)

```ts
// Cores das SÉRIES: escolhidas p/ contraste nos DOIS fundos → NÃO mudam com o tema
const CORES: Record<string, string> = {
  azul:   '#3B82F6',
  verde:  '#10B981',
  ambar:  '#F59E0B',
  rosa:   '#F43F5E',
  violeta:'#8B5CF6'
}

// MOLDURA (eixo, grade, tooltip): lida do tema atual — .light no <html>
function moldura() {
  const claro = document.documentElement.classList.contains('light')
  return {
    texto:         claro ? '#6B7280' : '#A0A3AC',
    grade:         claro ? 'rgba(17, 24, 39, 0.08)' : 'rgba(148, 163, 184, 0.12)',
    tooltipFundo:  claro ? '#FFFFFF' : '#26272B',
    tooltipTitulo: claro ? '#111827' : '#FFFFFF',
    tooltipTexto:  claro ? '#374151' : '#D1D5DB',
    tooltipBorda:  claro ? '#E5E7EB' : '#35363B'
  }
}
```

`MutationObserver` no `<html>` (filtro `['class']`) → redesenha ao trocar
claro/escuro. As séries não mudam, só a moldura.

### 10.2 Regras de render

- **Valor desenhado na barra** (plugin `afterDatasetsDraw`), não só no tooltip
  — num painel de leitura rápida, ter de passar o mouse anula o ganho.
  Fonte `600 11px ui-sans-serif`. Horizontal: à direita da barra
  (`el.x + 6`, `textAlign left`). Vertical: acima (`el.y - 5`, `textBaseline bottom`).
- `legend.display: false` sempre (barras). `precision: 0` nos ticks.
- `border.display: false` nos eixos. Grade só no eixo "de valor"
  (horizontal → eixo x; vertical → eixo y).
- Barras: `borderRadius: 5`, `maxBarThickness: horizontal ? 16 : 34`.
- `layout.padding`: horizontal `{ right: 42 }`, vertical `{ top: 18 }` (espaço p/ o rótulo).
- **Rosca**: `cutout: '62%'`, `hoverOffset: 6`, `borderWidth: 0`,
  `legend.display: false` — a legenda vai como **HTML ao lado do canvas**
  (texto em `<canvas>` não responde a classe Tailwind e fica ilegível num dos
  temas). Canvas fixo `140×140px`.

### 10.3 Template

```html
<template>
  <figure class="rounded-xl border border-border bg-background p-3 m-0">
    <figcaption class="text-[11px] font-bold uppercase tracking-wide text-muted-foreground mb-2">
      {{ spec.titulo }}
    </figcaption>

    <!-- Rosca: canvas fixo (só fatias) + legenda HTML -->
    <div v-if="ehRosca" class="flex items-center gap-4">
      <div class="shrink-0" style="width: 140px; height: 140px;">
        <canvas ref="canvasRef" />
      </div>
      <ul class="space-y-2 m-0 p-0 list-none min-w-0">
        <li v-for="item in legendaRosca" :key="item.rotulo" class="flex items-center gap-2 min-w-0">
          <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ background: item.cor }" />
          <span class="text-[12px] text-foreground truncate">{{ item.rotulo }}: {{ item.valor }} ({{ item.pct }}%)</span>
        </li>
      </ul>
    </div>

    <!-- Barras: altura fixa 190px (vertical) ou labels*26+40 (horizontal, mín 140) -->
    <div v-else :style="{ height: (spec.tipo === 'barras_h' ? Math.max(140, spec.labels.length * 26 + 40) : 190) + 'px' }">
      <canvas ref="canvasRef" />
    </div>
  </figure>
</template>
```

`defineExpose({ paraImagem })` → `chart.toBase64Image('image/png', 1)` para o PDF.

### 10.4 Como o backend monta cada gráfico (`_extrair_graficos`)

| Ferramenta que rodou | Gráfico(s) gerado(s) | Tipo · cor · sufixo |
|---|---|---|
| `ranking_vendedores` | "Conversas por vendedor" (só vendedores c/ conversas > 0, mín. 2) | `barras` · azul |
| " | "Tempo médio de resposta" (se ≥ 2 têm o dado) | `barras` · ambar · " min" |
| `ranking_sdrs` | "Conversas por SDR" | `barras` · azul |
| " | "Tempo médio de resposta por SDR" | `barras` · ambar · " min" |
| `conversas_paradas` | "{Minutos\|Horas\|Dias} sem interação" (top 10 mais paradas) | `barras_h` · rosa · unidade escolhida pela maior barra |
| `timeline_conversa` | "Quem falou na conversa" (Cliente / Vendedor / IA, se ≥ 2 fatias) | `rosca` · azul/verde/violeta |

Rótulos de eixo: primeiro nome do vendedor (máx. 14 ch); nome do canal truncado
em 16 ch p/ SDR; contato = primeiro nome ou `…{4 últimos dígitos}` do telefone.
`conversas_paradas` guarda `parada_minutos` cru e o gráfico escolhe a unidade
(< 2h → min; < 2 dias → h; senão dias), com 1 casa decimal se a faixa < 10.

---

## 11. Botões de exportação (no painel)

```html
<!-- por resposta -->
<div v-if="!t.erro" class="flex justify-end">
  <button @click="baixarPDF(t, i)" :disabled="exportando === t.id"
    class="inline-flex items-center gap-2 text-[12px] font-semibold text-primary bg-primary/10 hover:bg-primary/15 border border-transparent hover:border-primary/40 rounded-lg px-3 py-1.5 transition disabled:opacity-60">
    <svg v-if="exportando !== t.id" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M7 10l5 5 5-5" /><path d="M12 15V3" />
    </svg>
    <svg v-else class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
      <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75" />
    </svg>
    {{ exportando === t.id ? 'Gerando...' : (respostasValidas > 1 ? 'Baixar esta resposta' : 'Baixar PDF') }}
  </button>
</div>

<!-- sessão inteira: só a partir da 2ª resposta -->
<div v-if="respostasValidas > 1 && !pensando" class="pt-1">
  <button @click="baixarSessaoPDF" :disabled="exportando === 'sessao'"
    class="w-full inline-flex items-center justify-center gap-2 text-[12px] font-semibold text-foreground bg-muted/60 hover:bg-muted border border-border hover:border-primary/40 rounded-lg px-3 py-2 transition disabled:opacity-60">
    <svg v-if="exportando !== 'sessao'" class="w-3.5 h-3.5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><path d="M9 15h6M9 11h3" />
    </svg>
    <svg v-else class="w-3.5 h-3.5 animate-spin text-primary" viewBox="0 0 24 24" fill="none"><!-- spinner --></svg>
    {{ exportando === 'sessao' ? 'Gerando análise completa...' : `Baixar análise completa (${respostasValidas} respostas)` }}
  </button>
</div>
```

`respostasValidas` = turnos `assistant` sem `erro`. Turno com erro não é análise.

---

## 12. Exportação em PDF (`useAnalista.ts`)

`jspdf@^3` (retrato, A4) + `jspdf-autotable@^5` (tabelas do markdown de
reserva) + `chart.js` rasterizado num canvas fora da tela. **Importados sob
demanda** (`await import(...)`) — não entram no bundle inicial.

### 12.1 Constantes e marca

```ts
const ROXO: [number, number, number] = [102, 90, 228]   // marca Razy no PDF
const L = 16                     // margem esquerda (mm)
const LARGURA = 210 - L * 2      // = 178 mm (A4 retrato)
const RODAPE = 275               // a partir daqui, quebra a página
```

### 12.2 Cabeçalho (toda geração)

```
faixa ROXO 0,0 → 210×30 preenchida
"Razy"                       17pt bold branco  em (L, 14)
"Analise de Atendimento"     10pt normal branco em (L, 22)
título (a pergunta, ou "Analise completa da sessao")  13pt bold  em (L, 40)
subtítulo "Gerado em {data pt-BR}"  8.5pt cinza
```

### 12.3 Números de destaque (cartões no topo do conteúdo)

Saem **das séries dos gráficos** (que já vieram do banco), nunca do texto do
modelo — assim o destaque nunca diverge do gráfico. Até 6, em grade de 3
colunas. Rosca → "Maior parte: {label} — {pct}%". Barras → "{título} - maior"
e "{título} - menor". Cobertura → "Mensagens lidas: {lidas} de {total}".
Caixa: `roundedRect` fill `[250,250,252]` stroke `[228,228,234]`; valor 10pt
bold `[35,35,40]`; rótulo 7pt `[120,120,128]`.

### 12.4 Faixa de leitura parcial (quando `sem_conteudo > 0`)

`roundedRect` fill `[255,248,230]` stroke `[240,200,120]`; título 9.5pt bold
`[150,90,10]` "Leitura parcial: {lidas} de {total} mensagens ({pct}%)";
linha 2 8pt `[120,100,70]`.

### 12.5 Cards no PDF — mesmos tons da tela, em RGB sobre branco

```ts
const TOM: Record<string, { borda: [n,n,n]; fundo: [n,n,n]; titulo: [n,n,n] }> = {
  azul:     { borda: [191, 214, 252], fundo: [244, 248, 255], titulo: [29, 78, 216] },
  roxo:     { borda: [214, 202, 250], fundo: [249, 246, 255], titulo: [109, 40, 217] },
  verde:    { borda: [178, 229, 209], fundo: [243, 251, 248], titulo: [4, 120, 87] },
  amarelo:  { borda: [246, 219, 165], fundo: [255, 251, 240], titulo: [180, 83, 9] },
  vermelho: { borda: [248, 197, 208], fundo: [255, 245, 247], titulo: [190, 24, 60] },
  cinza:    { borda: [226, 226, 232], fundo: [250, 250, 252], titulo: [55, 65, 81] }
}
// mesmo mapeamento tipo→tom da tela:
// visao_geral|proxima_acao → azul · esclarecer → amarelo · resumo → roxo · coletado → cinza
// interesse → alta:verde / baixa:vermelho / else amarelo
// atencao   → alta:vermelho / baixa:verde / else amarelo
```

Cada card: mede a altura antes de desenhar (campos ≈ `ceil(n/2)*9`, itens e
texto por `splitTextToSize`), quebra página se não couber
(`y + altura > RODAPE`), desenha `roundedRect` fill/stroke do tom, título 9.5pt
bold (etiqueta " [chance media]" quando `interesse` + `nivel`), campos em 2
colunas (rótulo 6.5pt maiúsculo cinza + valor 8.5pt), itens com "- ", texto 8.5pt.

### 12.6 Tabelas (só no markdown de reserva)

`autoTable` — `headStyles.fillColor: ROXO`, `textColor: 255`, `theme: 'striped'`,
`alternateRowStyles.fillColor: [249,250,251]`, `styles.fontSize: 8.5`.

### 12.7 Gráficos no PDF — rasterizados à parte (moldura sempre clara)

Renderiza num `<canvas>` fora da tela (900px de largura, altura por tipo:
horizontal `max(260, labels*42+80)`, senão 380), **fundo branco explícito**
(`ctx.fillRect` — canvas transparente vira preto no jsPDF), `animation: false`,
`responsive: false`. Eixo `#4B5563` 18px, grade `rgba(17,24,39,0.10)`. Valor
desenhado `bold 17px Helvetica` `#1F2937` (não há hover no papel). Rosca:
legenda à direita, `#374151` 18px, texto `"{label}: {v} ({pct}%)"`.
Mesma paleta de séries da tela (`#3B82F6 #10B981 #F59E0B #F43F5E #8B5CF6`).
Cada gráfico ocupa `LARGURA` de largura; altura pela proporção real.

### 12.8 PDF de sessão (várias perguntas)

Ganha um **índice** ("NESTE RELATORIO", máx. 12 linhas + "+ N nas páginas
seguintes") e cada pergunta vira seção numerada ("PERGUNTA {n}" em ROXO 7.5pt,
+ enunciado 11.5pt, + linha separadora). Turnos com erro ficam de fora.

### 12.9 Rodapé (todas as páginas)

`"Razy - Analise de Atendimento"` à esquerda e `"{p} de {total}"` à direita,
7.5pt `[150,150,150]`, em `y = 288`.

### 12.10 Nome do arquivo

`analise-{slug da pergunta}-{AAAA-MM-DD}.pdf` /
`analise-completa-{slug}-{AAAA-MM-DD}.pdf`. `slug` = minúsculas, só `[a-z0-9-]`,
40 ch. `pdfSafe()` remove emojis/símbolos fora de Latin-1 (a fonte do jsPDF não
os renderiza) mas mantém acentos.

### 12.11 Funções exportadas

```ts
export async function exportarAnalisePDF(turno: TurnoAnalista, pergunta: string): Promise<void>
export async function exportarSessaoPDF(turnos: TurnoAnalista[]): Promise<void>
```

---

## 13. Informações sobre os atendentes (vendedor × SDR)

Distinção que o design carrega inteira:

| | **Vendedor** | **SDR** |
|---|---|---|
| O que é | profissional com número/instância própria (página Profissionais) | canal WhatsApp **sem** profissional vinculado (aba Canais) |
| Sinônimos | atendente, corretor, consultor, profissional | — |
| Conversa | tem `assigned_to_professional_id` | responde o canal/IA; agrupa por `instancia_id` |
| Cor no catálogo | verde (`chart`) | índigo (`sdr`) |
| Ferramentas | `buscar_vendedor`, `metricas_vendedor`, `ranking_vendedores` | `buscar_sdr`, `metricas_sdr`, `ranking_sdrs` |
| Conversas de um atendente | `listar_conversas(vendedor_id=…)` | `listar_conversas(sdr_id=…)` |

São **conjuntos separados** — um nunca entra na conta do outro. `ranking_sdrs`
já devolve os totais somados (`total_abertas`, `total_conversas`) porque
"quantos atendimentos os SDRs têm aberto no total?" é a pergunta mais comum e o
LLM erra soma linha a linha.

Números que cada consulta devolve (viram `campos` nos cards de comparação e
séries nos gráficos): carteira / conversas, ativas nas últimas 24h, paradas há
+ 3 dias, `resposta_media_min` (intervalo entre a msg do cliente e a próxima do
atendente — a métrica mais confiável, sai do horário gravado), `cobertura_pct`,
e `canal_status` (canal desconectado faz o atendente parecer ocioso mesmo
trabalhando — a resposta separa as duas coisas).

Para pergunta que pede **nome de contato** ("com quem esse SDR mais
conversou", "algum potencial") o prompt obriga `listar_conversas` — responder
com total quando se pediu nome não responde à pergunta.

---

## 14. Informações sobre um contato específico

### 14.1 A ponte: `useConversaAtiva.ts`

`useState('conversa_ativa')` — a **mesma ref** em qualquer componente. A página
de Conversas grava a conversa selecionada; o Analista (que vive no layout) lê:

```ts
export interface ConversaAtiva { id: string; numero: string; nome: string | null; vendedor: string | null }

export function useConversaAtiva() {
  const conversaAtiva = useState<ConversaAtiva | null>('conversa_ativa', () => null)
  function definir(c: ConversaAtiva | null) { conversaAtiva.value = c }
  function limpar() { conversaAtiva.value = null }
  return { conversaAtiva, definir, limpar }
}

// 5511912345678 → +55 11 91234-5678  (9 dígitos → 5+4; 8 dígitos → 4+4)
export function formatarTelefoneBR(numero: string | null | undefined): string { /* ... */ }
```

No `ConversasManager.vue`: `watch(conversaSelecionada, ...)` chama
`definirConversaAtiva({ id, numero, nome: nome_contato, vendedor })` com
`{ immediate: true }`; `onUnmounted` e o ramo `else` chamam
`limparConversaAtiva()` — sai da tela de Conversas → o analista volta às
perguntas gerais.

Efeitos no design: aparece o **card de contexto** (6.2), o botão flutuante sobe
para `bottom-44`, e o grupo 1 do catálogo passa a citar aquele telefone.

### 14.2 Contexto entre turnos (o serviço é stateless)

O painel guarda `contexto: ContextoConversa[]` (as conversas já identificadas
na sessão) e reenvia a cada pergunta. Sem isso, "quem mais falou nessa
conversa?" não teria referente. `limpar()` zera turnos **e** contexto juntos.

```ts
interface ContextoConversa { id: string; nome_contato?: string|null; numero?: string|null; vendedor?: string|null }
```

### 14.3 O que a resposta sobre um contato traz

`buscar_conversa_por_telefone` → `timeline_conversa` (lê as mensagens) →
card `visao_geral` (código, ver 9.5) + cards `resumo` / `coletado` /
`interesse` / `atencao` / `proxima_acao` (LLM) + gráfico rosca "Quem falou na
conversa". Se o número tem **várias conversas** (um canal por vendedor), o
prompt manda tratar cada uma ou perguntar qual — nunca escolher em silêncio.

---

## 15. "Qual é o potencial do cliente?" (chance de fechamento)

Pergunta do catálogo: **`O cliente do telefone {tel} tem chance de fechar?`**

### 15.1 Como o resultado aparece

Card **`interesse`**, título padrão "Interesse e chance de fechamento":

| `nivel` | Tom do card | Badge |
|---|---|---|
| `alta` | **verde** (`emerald`) | "Chance alta" |
| `media` | **amarelo** (`amber`) | "Chance média" |
| `baixa` | **vermelho** (`rose`) | "Chance baixa" |

O corpo vem em `itens` — cada item é **um sinal concreto**, citando a mensagem
que o originou. Ícone do card: gráfico de linha subindo
(`M3 3v18h18` + `M7 14l4-4 3 3 5-6`).

### 15.2 Regras do prompt (para o outro app replicar o comportamento)

- **Nunca dar porcentagem** ("70% de chance") — não há histórico de desfecho no
  sistema para sustentar previsão. Só sinais favoráveis e contrários.
- O caminho obrigatório: `listar_conversas` com `ordenar="engajamento"` (ordena
  por mensagens **escritas pelo cliente** — quem escreve está interessado; quem
  só recebeu disparo, não) → `timeline_conversa` nas 2–3 primeiras para **ler**
  o que o cliente disse → só então avaliar, citando as falas.
- Ignorar como oportunidade quem tem `cliente_nunca_respondeu = true`.
- Dizer **nome e telefone** de cada candidato — o dono precisa saber com quem
  falar, não quantos existem.

---

## 16. Contrato de dados (TypeScript — `useAnalista.ts`)

```ts
export interface SerieGrafico { nome: string; dados: number[]; cor?: string; cores?: string[] }
export interface GraficoSpec {
  tipo: 'barras' | 'barras_h' | 'rosca'
  titulo: string
  labels: string[]
  series: SerieGrafico[]
  sufixo?: string
}

export type TipoCard = 'visao_geral' | 'resumo' | 'coletado' | 'interesse' | 'atencao' | 'proxima_acao' | 'esclarecer'

export interface CardAnalista {
  tipo: TipoCard
  titulo: string
  nivel?: 'alta' | 'media' | 'baixa' | null   // interesse: chance · atencao: gravidade
  texto?: string | null
  itens?: string[]
  campos?: { rotulo: string; valor: string }[]
}

export interface Cobertura { total: number; lidas: number; sem_conteudo: number }
export interface PassoRastro { fn: string; args: string; resultado: string }   // auditoria — NÃO exibido na tela, vai no PDF
export interface ContextoConversa { id: string; nome_contato?: string|null; numero?: string|null; vendedor?: string|null }

export interface RespostaAnalista {
  resposta: string          // markdown de reserva (erro / ai-service antigo)
  cards: CardAnalista[]
  rastro: PassoRastro[]
  cobertura: Cobertura | null
  graficos: GraficoSpec[]
  titulo: string
  contexto?: ContextoConversa[]
}

export interface TurnoAnalista {
  id: string
  papel: 'user' | 'assistant'
  texto: string
  cards?: CardAnalista[]
  rastro?: PassoRastro[]
  cobertura?: Cobertura | null
  graficos?: GraficoSpec[]
  titulo?: string
  erro?: boolean
}

export interface ResumoOperacao {
  ativas: number | null
  movimento_24h: number | null
  paradas_3d: number | null
  canais_on: number | null
  canais_total: number | null
  vendedores: number | null
  total_msgs: number | null
  msgs_sem_texto: number | null
  cobertura_pct: number | null
  resposta_media_min: number | null
  historico_desde: string | null
}
```

### `useAnalista()` retorna

`{ turnos, resumo, pensando, carregarResumo, perguntar, limpar }`.
`perguntar()` faz push do turno `user`, envia
`{ pergunta, historico (últimos 8, só papel+texto), contexto }` para
`POST /api/analista/perguntar`, e faz push do turno `assistant`.

---

## 17. Endpoints

### Nuxt (proxy — valida o JWT do Supabase e injeta `usuario_id`)

```
GET  /api/analista/resumo       → ai-service GET  /analista/resumo?usuario_id=…
POST /api/analista/perguntar    → ai-service POST /analista/perguntar
       body: { pergunta, historico?[], contexto?[] }
```

O `resumo` **falha em silêncio** (retorna `null`) — é informação de apoio, o
painel abre e aceita perguntas mesmo sem ele. O `perguntar` traduz erros do
ai-service para algo acionável (404 → "faça o deploy do ai-service"; 401/403 →
"confira o INTERNAL_TOKEN"; timeout 90s → "pergunta mais específica").

### ai-service (FastAPI, interno — header `X-Internal-Token`)

```
GET  /analista/resumo       → consultas.resumo_operacao (SQL puro, sem LLM, instantâneo)
POST /analista/perguntar    → analista.perguntar (LLM + ferramentas)
```

Modelo: `gpt-6-luna` com `reasoning_effort: "none"` (único modo em que ele aceita
tools no Chat Completions) e sem `temperature`, `response_format` = JSON schema
fechado (`cards[]`), teto de 5 idas ao LLM. Usa a chave OpenAI do **painel** do
usuário (Configurações → Integrações), com fallback para a do `.env`.

### Arquitetura de segurança (por que o LLM nunca vê o banco)

`pergunta → LLM escolhe uma FERRAMENTA → SQL fixo roda → LLM lê o retorno → cards`.
O LLM nunca escreve SQL. `usuario_id` é injetado pelo servidor a partir do JWT —
jamais vem do texto digitado. Resolve de uma vez o isolamento entre empresas e
a injeção de prompt (o conteúdo de `mensagens` é escrito por terceiros).
`rastro` e `cobertura` são montados **por código** a partir das tool calls
reais — se viessem do texto do modelo, ele poderia arredondar/inventar
justamente o número que serve para desconfiar dele.

### Ferramentas expostas ao LLM (nomes)

`resumo_operacao`, `buscar_conversa_por_telefone`, `buscar_conversas`,
`timeline_conversa`, `buscar_vendedor`, `metricas_vendedor`,
`ranking_vendedores`, `buscar_sdr`, `metricas_sdr`, `ranking_sdrs`,
`listar_conversas`, `conversas_paradas`.

---

## 18. Checklist de portabilidade

1. **Tokens de cor** (seção 2) — ou o mapa de hex equivalente.
2. **Bolha + painel + transições** (4, 5) — `translate-x-full`, larguras
   `700/980/100vw`, `z-40`/`z-50`, Escape fecha.
3. **Tela de abertura** (6) — título, card de contexto, 4 tiles com
   `TILE_CLASSES` + lógica de tom pelo valor, faixa de cobertura, catálogo.
4. **Catálogo de perguntas** (7) — 4 grupos, grupo 1 contextual, `GRUPO_CLASSES`,
   a "dica" que prepara o input em vez de enviar.
5. **`CardAnalista`** (9) — `TONS` (classes por extenso), `tom(tipo,nivel)`,
   `badge`, template com `dl`/`ul`/`esclarecer`/`texto`; card `visao_geral`
   montado por código.
6. **`GraficoAnalista`** (10) — `CORES` fixas × `moldura()` do tema,
   `MutationObserver` no `<html>`, valor desenhado na barra, rosca com legenda
   HTML, alturas do `<figure>`.
7. **Exportação PDF** (12) — marca `ROXO [102,90,228]`, `L=16`/`LARGURA=178`/
   `RODAPE=275`, destaques das séries, `TOM` RGB dos cards, gráficos
   rasterizados com moldura clara, índice na sessão, rodapé paginado.
8. **Contrato de dados** (16) e **endpoints** (17) — se for reaproveitar o
   backend; senão, só garanta que a resposta chegue no formato `RespostaAnalista`.
```

Ícones: todos SVG inline `viewBox="0 0 24 24"`, `stroke="currentColor"`,
`stroke-width="2"`, `stroke-linecap/linejoin="round"`. Spinner = `<circle r=10
opacity-25>` + `<path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
opacity-75>` com `animate-spin`. Nenhuma biblioteca de ícones.
