# Card do Assistente — Robozinho animado (código exato)

Documento com **o código CSS/HTML exato** do rostinho do robô usado nos cards
de assistentes: cabeça, orelhas, olhos piscando, boca sorrindo, brilho varrendo
o rosto, "flutuar", estado dormindo (offline) com Zzz, balão "Me acorde!",
estado chorando (hover na lixeira) e estado feliz (hover no card).

> Origem: componente Vue `AssistenteCard.vue` (Nuxt + Tailwind `darkMode: 'class'`).
> Aqui está tudo isolado para você colar em **qualquer** app. As animações são
> CSS puro — funcionam sem framework. Só a lógica das variáveis de defasagem
> (para cada robô piscar fora de sincronia) usa um pouco de JS.

---

## 1. Estrutura HTML da cabeça (a "carinha")

Esta é a árvore de elementos que forma o robô. Cole dentro de um container.

```html
<div class="robot-head" aria-hidden="true">
  <div class="antenna"></div>
  <div class="ear left"></div>
  <div class="ear right"></div>
  <div class="head">
    <div class="face">
      <span class="eye left"></span>
      <span class="eye right"></span>
      <span class="mouth"></span>
      <span class="tear left"></span>
      <span class="tear right"></span>
    </div>
  </div>
  <div class="mic"></div>
</div>
```

- `antenna` — a antena curva no topo.
- `ear left/right` — as orelhinhas laterais (cor muda por tipo do assistente).
- `head` — a cabeça branca arredondada.
- `face` — o "visor" preto onde ficam olhos + boca.
- `eye left/right` — os dois olhos (piscam sozinhos).
- `mouth` — a boca (sorriso que se mexe de leve).
- `tear left/right` — lágrimas (escondidas; só caem no estado "chorando").
- `mic` — o microfone/gancho embaixo.

### Estados opcionais
- Para o robô **dormir** (offline), adicione a classe `is-off` no elemento pai
  que envolve o `.robot-head` (aqui chamado `.head-zone`).
- O container mais externo do card precisa da classe `group` — é ele quem
  dispara os efeitos de hover (feliz, acordar, chorar).

Exemplo do envelope:

```html
<div class="assistente-card group">
  <div class="head-zone">            <!-- adicione "is-off" quando offline -->
    <div class="robot-head" aria-hidden="true"> ... </div>

    <!-- Zzz: só quando dormindo (offline) -->
    <div class="zzz" aria-hidden="true">
      <span class="z z1">z</span>
      <span class="z z2">Z</span>
      <span class="z z3">Z</span>
    </div>

    <!-- Balão "Me acorde!": aparece no hover quando offline -->
    <button type="button" class="balao-religar" title="Religar assistente">
      <span class="balao-txt" aria-hidden="true">
        <!-- 1 span por letra, com --i = índice (0,1,2,...) -->
        <span class="balao-char" style="--i:0">M</span>
        <span class="balao-char" style="--i:1">e</span>
        <span class="balao-char" style="--i:2">&nbsp;</span>
        <span class="balao-char" style="--i:3">a</span>
        <span class="balao-char" style="--i:4">c</span>
        <span class="balao-char" style="--i:5">o</span>
        <span class="balao-char" style="--i:6">r</span>
        <span class="balao-char" style="--i:7">d</span>
        <span class="balao-char" style="--i:8">e</span>
        <span class="balao-char" style="--i:9">!</span>
      </span>
      <span class="balao-icon"><i class="fa-solid fa-power-off"></i></span>
    </button>
  </div>
</div>
```

---

## 2. Variáveis de sincronia (cada robô pisca fora de compasso)

Cada robô recebe **durações e atrasos ligeiramente diferentes** para que nunca
pisquem juntos. Os valores são derivados de um "seed" (o id/nome), então são
determinísticos (mesmo valor no servidor e no cliente — sem hydration mismatch).
`animation-delay` **negativo** faz cada um já começar num ponto diferente do
ciclo, sem pausa inicial.

Aplique estas custom properties no elemento raiz do card (`style="..."`):

| Variável        | O que controla        | Faixa sugerida |
|-----------------|-----------------------|----------------|
| `--float-dur`   | flutuar da cabeça     | 3.0s – 4.8s    |
| `--float-delay` | atraso do flutuar     | negativo       |
| `--blink-dur`   | piscar dos olhos      | 3.4s – 6.6s    |
| `--blink-delay` | atraso do piscar      | negativo       |
| `--smile-dur`   | balanço do sorriso    | 2.4s – 4.0s    |
| `--smile-delay` | atraso do sorriso     | negativo       |
| `--shine-dur`   | brilho varrendo rosto | 3.0s – 5.2s    |
| `--shine-delay` | atraso do brilho      | negativo       |
| `--ear-from`    | cor topo da orelha    | (por tipo)     |
| `--ear-to`      | cor base da orelha    | (por tipo)     |

### JS para gerar as variáveis (opcional, mas recomendado)

```js
// Gera as CSS vars de animação a partir de um seed estável (id ou nome).
// Retorna um objeto { '--float-dur': '3.62s', ... } para virar inline style.
function animVars(seedStr) {
  seedStr = seedStr || 'x'
  let h = 0
  for (let i = 0; i < seedStr.length; i++) h = (h * 31 + seedStr.charCodeAt(i)) >>> 0
  const frac = (shift) => ((h >>> shift) % 1000) / 1000
  const r1 = frac(0), r2 = frac(3), r3 = frac(7), r4 = frac(11), r5 = frac(15)

  const fDur  = 3.0 + r1 * 1.8   // flutuar:  3.0–4.8s
  const bDur  = 3.4 + r2 * 3.2   // piscar:   3.4–6.6s
  const sDur  = 2.4 + r3 * 1.6   // sorriso:  2.4–4.0s
  const shDur = 3.0 + r4 * 2.2   // brilho:   3.0–5.2s
  const s = (n) => `${n.toFixed(2)}s`

  return {
    '--float-dur':  s(fDur),
    '--float-delay': s(-(r1 * fDur)),
    '--blink-dur':  s(bDur),
    '--blink-delay': s(-(r2 * bDur)),
    '--smile-dur':  s(sDur),
    '--smile-delay': s(-(r3 * sDur)),
    '--shine-dur':  s(shDur),
    '--shine-delay': s(-(r5 * shDur)),
  }
}
```

> Se quiser tudo em CSS puro (sem JS), basta **não** definir as variáveis: cada
> animação tem um valor padrão no `var(..., fallback)`. Aí todos piscam juntos.
> Para variar sem JS, defina valores fixos diferentes por card na mão.

### Cores das orelhas por tipo (opcional)

```js
// Cada par é o gradiente [topo, base] da orelha.
const EAR_CORES = {
  principal:  ['#6366f1', '#4f20d9'], // indigo -> violeta
  comercial:  ['#10b981', '#0d9488'], // emerald -> teal
  financeiro: ['#f59e0b', '#ea580c'], // amber -> laranja
  suporte:    ['#0ea5e9', '#2563eb'], // sky -> azul
  pos_venda:  ['#f43f5e', '#db2777'], // rose -> pink
  outro:      ['#64748b', '#334155'], // slate
}
// -> style: { '--ear-from': from, '--ear-to': to }
```

---

## 3. CSS completo (colar como está)

Este é o CSS **exato** do robô. É `scoped` no Vue original, mas funciona igual
em CSS global. Se colar em um arquivo global, considere prefixar as regras
com um seletor de container (ex.: `.assistente-card ...`) para não vazar.

```css
/* ════════════════ CABEÇA (sem fundo) ════════════════ */
.head-zone {
  width: 100%;
  height: 94px;
  /* sem plano de fundo: a cabeça flutua direto sobre o corpo */
  transition: transform 0.28s ease;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.robot-head {
  position: relative;
  width: 188px;
  height: 150px;
  transform: scale(0.76);
  animation: headFloat var(--float-dur, 3.6s) ease-in-out infinite;
  animation-delay: var(--float-delay, 0s);
  filter: drop-shadow(0 12px 16px rgba(40, 28, 96, 0.18));
  transition: filter 0.3s ease;
}

/* ════════════ DORMINDO (offline): respira devagar, olhos fechados, Zzz ════════════ */
.is-off .robot-head {
  filter: grayscale(0.35) brightness(0.97) drop-shadow(0 12px 16px rgba(40, 28, 96, 0.12));
  /* troca o "flutuar" por uma respiração lenta -> ar de quem dorme */
  animation: sleepBreath 4.6s ease-in-out infinite;
  animation-delay: var(--float-delay, 0s);
}
.is-off .face::after { animation: none; }   /* sem brilho varrendo o rosto */
/* Olhos fechados em arquinho "‿" */
.is-off .eye {
  animation: none;
  height: 5px;
  top: 27px;
  background: transparent;
  border-bottom: 3px solid #7fd5ec;
  border-radius: 0 0 12px 12px;
  box-shadow: none;
}
/* Boquinha pequena e relaxada */
.is-off .mouth {
  animation: none;
  width: 22px;
  height: 9px;
  left: 45px;
  top: 45px;
  border-bottom-width: 3px;
  border-radius: 0 0 16px 16px;
}

/* Zzz subindo (só quando dormindo) */
.zzz {
  position: absolute;
  top: 0; right: 46px;
  width: 44px; height: 56px;
  pointer-events: none;
  z-index: 20;
  transition: opacity 0.3s ease;
}
.zzz .z {
  position: absolute;
  font-weight: 800;
  font-family: system-ui, "Segoe UI", sans-serif;
  color: #94a3b8;
  opacity: 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
  animation: zzzFloat 3s ease-in-out infinite;
}
.zzz .z1 { font-size: 11px; left: 0;   bottom: 6px;  animation-delay: 0s; }
.zzz .z2 { font-size: 14px; left: 9px;  bottom: 16px; animation-delay: 0.55s; }
.zzz .z3 { font-size: 18px; left: 20px; bottom: 28px; animation-delay: 1.1s; }

/* ════════ ACORDA NO HOVER (dica visual de "clique em religar") ════════ */
/* Passar o mouse no card de um robô dormindo o "acorda": some o Zzz, tira o
   cinza (ele liga), abre os olhos e dá um sorrisinho. */
.group:hover .zzz { opacity: 0; }
.group:hover .head-zone.is-off .robot-head {
  filter: drop-shadow(0 12px 16px rgba(40, 28, 96, 0.18));   /* sem grayscale = "ligou" */
}
.group:hover .head-zone.is-off .eye {
  animation: none;
  height: 20px;
  top: 20px;
  background: #22d3ff;
  border: 0;
  border-radius: 50%;
  box-shadow: 0 0 16px #22d3ff;
}
.group:hover .head-zone.is-off .mouth {
  animation: none;
  width: 28px;
  height: 13px;
  left: 42px;
  top: 41px;
  border-bottom: 4px solid #22d3ff;
  border-radius: 0 0 20px 20px;
}

/* Balão "Me acorde!" — escondido por padrão, aparece no hover (só offline) */
.balao-religar {
  position: absolute;
  top: 2px; right: 2px;
  z-index: 25;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 13px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  box-shadow: 0 12px 26px rgba(20, 20, 60, 0.18);
  cursor: pointer;
  opacity: 0;
  transform: scale(0.85) translateY(8px);
  transform-origin: top right;
  /* entrada mais suave */
  transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  pointer-events: none;
  /* cores (adapte ao seu tema): */
  background: #fff;
  color: #334155;
  border: 1px solid #e2e8f0;
}
/* rabicho do balão apontando pra cabeça */
.balao-religar::after {
  content: "";
  position: absolute;
  left: 18px; bottom: -5px;
  width: 10px; height: 10px;
  background-color: inherit;
  border-bottom: 1px solid;
  border-left: 1px solid;
  border-color: inherit;
  transform: rotate(-45deg);
  border-bottom-left-radius: 2px;
}
.balao-txt { display: inline-flex; }
.balao-char {
  display: inline-block;
  opacity: 0;
  transform: translateY(2px);
}
/* digitação: cada letra entra com um pequeno atraso escalonado, após o balão */
.group:hover .balao-char {
  animation: charIn 0.24s ease forwards;
  animation-delay: calc(0.2s + var(--i) * 0.05s);
}
.balao-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px; height: 24px;
  border-radius: 999px;
  background: #10b981;
  color: #fff;
  font-size: 12px;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5);
  animation: balaoPulse 1.2s ease-in-out infinite;
}
.group:hover .balao-religar {
  opacity: 1;
  transform: scale(1) translateY(0);
  pointer-events: auto;
}

/* ════════════════ PEÇAS DO ROBÔ ════════════════ */
.antenna {
  position: absolute;
  width: 80px; height: 60px;
  left: 54px; top: 0;
  border-top: 7px solid #28215a;
  border-radius: 70px 70px 0 0;
}
.head {
  position: absolute;
  width: 150px; height: 108px;
  background: linear-gradient(145deg, #ffffff, #e6e0ff);
  border-radius: 48px;
  left: 19px; top: 34px;
  box-shadow: inset 0 -8px 18px rgba(91, 33, 232, 0.12);
}
.face {
  position: absolute;
  width: 112px; height: 66px;
  background: #111124;
  border-radius: 30px;
  left: 19px; top: 22px;
  overflow: hidden;
}
.face::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.15) 45%, transparent 70%);
  transform: translateX(-100%);
  animation: faceShine var(--shine-dur, 3.5s) ease-in-out infinite;
  animation-delay: var(--shine-delay, 0s);
}
.eye {
  position: absolute;
  width: 14px; height: 22px;
  background: #22d3ff;
  border-radius: 50%;
  top: 20px;
  box-shadow: 0 0 14px #22d3ff;
  transition: height 0.25s ease, top 0.25s ease, border-radius 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
  animation: blink var(--blink-dur, 4s) infinite;
  animation-delay: var(--blink-delay, 0s);
}
.eye.left { left: 30px; }
.eye.right { right: 30px; }
.mouth {
  position: absolute;
  width: 32px; height: 16px;
  border-bottom: 5px solid #22d3ff;
  border-radius: 0 0 28px 28px;
  left: 40px; top: 40px;
  transition: width 0.25s ease, height 0.25s ease, left 0.25s ease, top 0.25s ease, border-radius 0.25s ease, background 0.25s ease;
  animation: smileMove var(--smile-dur, 2.8s) ease-in-out infinite;
  animation-delay: var(--smile-delay, 0s);
}
.ear {
  position: absolute;
  width: 24px; height: 50px;
  background: linear-gradient(180deg, var(--ear-from, #8b5cf6), var(--ear-to, #4f20d9));
  top: 56px;
  border-radius: 18px;
  box-shadow: inset 0 0 10px rgba(255, 255, 255, 0.25);
}
.ear.left { left: 4px; }
.ear.right { right: 4px; }
.mic {
  position: absolute;
  width: 48px; height: 36px;
  border-left: 5px solid #262159;
  border-bottom: 5px solid #262159;
  border-radius: 0 0 0 28px;
  left: 16px; top: 96px;
}
.mic::after {
  content: "";
  position: absolute;
  width: 20px; height: 10px;
  background: #262159;
  border-radius: 18px;
  left: -6px; bottom: -8px;
}

/* ════════════════ EXPRESSÃO AO PASSAR O MOUSE (card inteiro = .group) ════════════════ */
/* O robô fica "feliz": olhos viram arquinhos ⌒⌒ e o sorriso abre mais.
   `animation: none` solta o piscar/sorriso pra a expressão fixar. */
.group:hover .head-zone {
  transform: scale(1.05) translateY(-2px);
}
.group:hover .head-zone:not(.is-off) .eye {
  animation: none;
  height: 10px;
  top: 24px;
  border-radius: 14px 14px 3px 3px;   /* arco pra cima = olho feliz ⌒ */
  box-shadow: 0 0 20px #22d3ff;
  background: #5eeaff;
}
.group:hover .head-zone:not(.is-off) .mouth {
  animation: none;
  width: 40px;
  height: 20px;
  left: 36px;
  top: 38px;
  border-bottom-width: 6px;
  border-radius: 0 0 30px 30px;        /* só a curva do sorriso, mais larga e funda */
}

/* ════════════ CHORANDO (hover na lixeira) — muda a carinha lá em cima ════════════ */
/* Lágrimas (escondidas por padrão; caem só quando a lixeira é "hoverada") */
.tear {
  position: absolute;
  width: 7px; height: 10px;
  background: linear-gradient(180deg, #7dd3fc, #38bdf8);
  border-radius: 60% 60% 60% 60% / 70% 70% 40% 40%;
  top: 36px;
  opacity: 0;
  box-shadow: 0 0 6px rgba(56, 189, 248, 0.7);
  pointer-events: none;
}
.tear.left { left: 34px; }
.tear.right { right: 34px; }
/* :has() detecta o hover na lixeira lá embaixo e muda a carinha lá em cima.
   O botão de excluir precisa ter a classe `.btn-excluir`. */
.group:hover:has(.btn-excluir:hover) .head-zone .eye {
  animation: none;
  height: 22px;
  top: 18px;
  border: 0;
  border-radius: 50%;
  background: #7dd3fc;                 /* olhos marejados */
  box-shadow: 0 0 16px #38bdf8;
}
.group:hover:has(.btn-excluir:hover) .head-zone .mouth {
  animation: none;
  width: 26px;
  height: 10px;
  left: 43px;
  top: 48px;
  border-bottom: 0;
  border-top: 5px solid #22d3ff;
  border-radius: 14px 14px 0 0;        /* boca pra baixo = triste */
}
.group:hover:has(.btn-excluir:hover) .head-zone .tear {
  animation: tearFall 1.1s ease-in infinite;
}
.group:hover:has(.btn-excluir:hover) .head-zone .tear.right {
  animation-delay: 0.55s;
}
/* mira na lixeira: esconde o balão "Me acorde!" (não faz sentido chorando) */
.group:hover:has(.btn-excluir:hover) .balao-religar {
  opacity: 0;
  pointer-events: none;
}

/* ════════════════ ANIMAÇÕES (keyframes) ════════════════ */
@keyframes headFloat {
  0%, 100% { transform: scale(0.76) translateY(0) rotate(-1deg); }
  50% { transform: scale(0.76) translateY(-7px) rotate(1.5deg); }
}
@keyframes blink {
  0%, 88%, 100% { transform: scaleY(1); }
  92%, 96% { transform: scaleY(0.12); }
}
@keyframes smileMove {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(2px); }
}
@keyframes faceShine {
  0%, 45% { transform: translateX(-120%); }
  70%, 100% { transform: translateX(120%); }
}
@keyframes pulseOnline {
  0% { box-shadow: 0 0 0 0 rgba(18, 212, 103, 0.55); }
  70% { box-shadow: 0 0 0 8px rgba(18, 212, 103, 0); }
  100% { box-shadow: 0 0 0 0 rgba(18, 212, 103, 0); }
}
/* Respiração lenta do robô dormindo */
@keyframes sleepBreath {
  0%, 100% { transform: scale(0.76) translateY(0); }
  50% { transform: scale(0.764) translateY(1.5px); }
}
/* Zzz subindo e sumindo */
@keyframes zzzFloat {
  0% { opacity: 0; transform: translateY(8px) scale(0.7) rotate(-6deg); }
  20% { opacity: 0.85; }
  55% { opacity: 0.55; }
  100% { opacity: 0; transform: translateY(-18px) scale(1.05) rotate(8deg); }
}
/* Ícone de religar pulsando dentro do balão */
@keyframes balaoPulse {
  0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
  50% { transform: scale(1.18); box-shadow: 0 0 0 5px rgba(16, 185, 129, 0); }
}
/* digitação das letras do balão */
@keyframes charIn {
  from { opacity: 0; transform: translateY(2px); }
  to { opacity: 1; transform: translateY(0); }
}
/* lágrimas caindo (robô chorando) */
@keyframes tearFall {
  0% { opacity: 0; transform: translateY(0) scale(0.6); }
  25% { opacity: 1; }
  100% { opacity: 0; transform: translateY(28px) scale(1); }
}

/* Acessibilidade: respeita quem desativou animações no SO */
@media (prefers-reduced-motion: reduce) {
  .robot-head, .eye, .mouth, .face::after, .dot-on { animation: none !important; }
  .zzz .z { animation: none !important; opacity: 0.8 !important; }
  .balao-icon { animation: none !important; }
  .balao-char { animation: none !important; opacity: 1 !important; transform: none !important; }
  .tear { animation: none !important; }
}
```

---

## 4. Resumo dos comportamentos

| Efeito                    | Como dispara                                  | Elementos/regras envolvidas |
|---------------------------|-----------------------------------------------|-----------------------------|
| **Olhos piscando**        | Automático, contínuo                          | `.eye` + `@keyframes blink` (`scaleY` pra 0.12 rapidinho aos 92–96% do ciclo) |
| **Fora de sincronia**     | `--blink-dur`/`--blink-delay` por robô        | vars geradas no JS (`animVars`) |
| **Cabeça flutuando**      | Automático                                    | `.robot-head` + `@keyframes headFloat` |
| **Sorriso balançando**    | Automático                                    | `.mouth` + `@keyframes smileMove` |
| **Brilho varrendo o rosto** | Automático                                  | `.face::after` + `@keyframes faceShine` |
| **Feliz (olhos ⌒⌒)**      | Hover no card (`.group:hover`)                | regras `.group:hover ... .eye/.mouth` |
| **Dormindo**              | Classe `is-off` no `.head-zone`               | `.is-off` (olhos fechados, respira, cinza) |
| **Zzz subindo**           | Só com `is-off`                               | `.zzz .z` + `@keyframes zzzFloat` |
| **Acordar**               | Hover no card dormindo                         | `.group:hover .head-zone.is-off ...` |
| **Balão "Me acorde!"**    | Hover no card dormindo                          | `.balao-religar` + `charIn` + `balaoPulse` |
| **Chorando + lágrimas**   | Hover no botão `.btn-excluir` (lixeira)        | `:has(.btn-excluir:hover)` + `@keyframes tearFall` |

### Detalhes importantes de reprodução

1. **`.group` é obrigatório** no container externo — é o gatilho de todos os
   hovers (feliz, acordar, chorar). No Tailwind é a classe utilitária `group`;
   em CSS puro é só uma classe comum chamada `group`.
2. O botão de lixeira precisa ter a classe **`btn-excluir`** para o seletor
   `:has(.btn-excluir:hover)` funcionar (efeito chorando). `:has()` exige
   navegador moderno (Chrome/Edge/Safari/Firefox atuais).
3. As cores dos olhos/boca são **ciano `#22d3ff`** (aceso) e variações; o rosto
   é quase-preto `#111124`; a cabeça é branco→lilás. Ajuste ao seu tema.
4. Se **não** usar o JS de `animVars`, todos os robôs piscam em sincronia
   (os `var(..., fallback)` assumem valores fixos). Para variar sem JS, defina
   `--blink-dur`, `--blink-delay` etc. manualmente em cada card.
5. Escala: `.robot-head` usa `transform: scale(0.76)` — todas as animações de
   `headFloat`/`sleepBreath` **repetem esse scale** para não "pular" de tamanho.
   Se mudar a escala, atualize os keyframes também.
```
