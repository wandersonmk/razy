<template>
  <div :class="['assistente-card group', ativo ? 'is-online' : 'is-offline']" :style="cardStyle">
    <!-- ── Robô flutuante (carinha animada) ── -->
    <div :class="['head-zone', { 'is-off': !ativo }]">
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

      <!-- Zzz: só quando dormindo (offline) -->
      <div v-if="!ativo" class="zzz" aria-hidden="true">
        <span class="z z1">z</span>
        <span class="z z2">Z</span>
        <span class="z z3">Z</span>
      </div>

      <!-- Balão "Me acorde!": aparece no hover quando offline -->
      <button
        v-if="!ativo"
        type="button"
        class="balao-religar"
        title="Religar assistente"
        @click="$emit('toggle', assistente)"
      >
        <span class="balao-txt" aria-hidden="true">
          <span
            v-for="(ch, i) in acordeChars"
            :key="i"
            class="balao-char"
            :style="{ '--i': i }"
            v-html="ch"
          />
        </span>
        <span class="balao-icon">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9"/></svg>
        </span>
      </button>
    </div>

    <!-- Corpo do card -->
    <div class="corpo">
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0">
          <h3 class="text-base font-semibold text-foreground truncate">{{ assistente.nome || 'Assistente' }}</h3>
        </div>
        <span :class="['chip', ativo ? 'chip-on' : 'chip-off']">
          <span class="chip-dot" /> {{ ativo ? 'ONLINE' : 'OFFLINE' }}
        </span>
      </div>

      <!-- Badge de tipo -->
      <div class="mt-2">
        <span class="badge" :style="{ color: meta.cor, borderColor: meta.cor + '55', background: meta.cor + '14' }">
          <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a5 5 0 00-5 5v1H4a2 2 0 00-2 2v5a2 2 0 002 2h1v-2H4v-5h1v1a1 1 0 002 0V7a3 3 0 116 0v3a1 1 0 002 0V8h1v5h-1v2h1a2 2 0 002-2v-5a2 2 0 00-2-2h-1V7a5 5 0 00-5-5z"/></svg>
          {{ meta.label.toUpperCase() }}
        </span>
      </div>

      <!-- Ações -->
      <div class="mt-3 flex items-center justify-between">
        <button type="button" class="link-detalhes" @click="detalhes = !detalhes">
          {{ detalhes ? 'Ocultar detalhes' : 'Detalhes' }}
          <svg :class="['w-3.5 h-3.5 transition-transform', detalhes ? 'rotate-180' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
        </button>

        <div class="flex items-center gap-1">
          <button type="button" class="acao" :title="ativo ? 'Desligar' : 'Ligar'" @click="$emit('toggle', assistente)">
            <svg :class="['w-4 h-4', ativo ? 'text-amber-500' : 'text-green-500']" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9"/></svg>
          </button>
          <button type="button" class="acao" title="Editar" @click="$emit('editar', assistente.id)">
            <svg class="w-4 h-4 text-violet-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
          </button>
          <button type="button" class="acao btn-excluir" title="Excluir" @click="$emit('excluir', assistente)">
            <svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"/></svg>
          </button>
        </div>
      </div>

      <!-- Detalhes: instância vinculada -->
      <div v-if="detalhes" class="mt-3 pt-3 border-t border-border space-y-1.5 text-xs">
        <div v-if="assistente.instancia" class="flex items-center gap-2 text-muted-foreground">
          <span :class="['inline-block w-2 h-2 rounded-full', conectado ? 'bg-green-500' : 'bg-muted-foreground/40']" />
          <span class="text-foreground font-medium truncate">{{ assistente.instancia.nome_instancia }}</span>
          <span v-if="assistente.instancia.phone" class="tabular-nums">· {{ assistente.instancia.phone }}</span>
        </div>
        <div v-else class="flex items-center gap-2 text-amber-600 dark:text-amber-400">
          <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.72-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
          <span>Sem instância — atribua um número para operar</span>
        </div>
        <p class="text-muted-foreground/70">Criado em {{ dataCriacao }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Assistente } from '~/composables/useAssistentes'
import { tipoMeta } from '~/composables/useAssistentes'

const props = defineProps<{ assistente: Assistente }>()
defineEmits<{ editar: [id: string]; excluir: [a: Assistente]; toggle: [a: Assistente] }>()

const detalhes = ref(false)
const ativo = computed(() => !!props.assistente.ativo)
const meta = computed(() => tipoMeta(props.assistente.tipo))
const conectado = computed(() => props.assistente.instancia?.status === 'connected')
const dataCriacao = computed(() => {
  const d = props.assistente.created_at
  if (!d) return '—'
  try { return new Date(d).toLocaleDateString('pt-BR') } catch { return '—' }
})

// Texto do balão, uma letra por span (espaço vira &nbsp;)
const acordeChars = 'Me acorde!'.split('').map((c) => (c === ' ' ? '&nbsp;' : c))

// ── Cores das orelhas por tipo (gradiente topo → base) ──
const EAR_CORES: Record<string, [string, string]> = {
  principal: ['#6366f1', '#4f20d9'],
  comercial: ['#10b981', '#0d9488'],
  financeiro: ['#f59e0b', '#ea580c'],
  suporte: ['#0ea5e9', '#2563eb'],
  pos_venda: ['#f43f5e', '#db2777'],
  outro: ['#64748b', '#334155']
}

// ── Variáveis de sincronia a partir de um seed estável (id ou nome) ──
function animVars(seedStr: string): Record<string, string> {
  seedStr = seedStr || 'x'
  let hsh = 0
  for (let i = 0; i < seedStr.length; i++) hsh = (hsh * 31 + seedStr.charCodeAt(i)) >>> 0
  const frac = (shift: number) => ((hsh >>> shift) % 1000) / 1000
  const r1 = frac(0), r2 = frac(3), r3 = frac(7), r4 = frac(11), r5 = frac(15)

  const fDur = 3.0 + r1 * 1.8
  const bDur = 3.4 + r2 * 3.2
  const sDur = 2.4 + r3 * 1.6
  const shDur = 3.0 + r4 * 2.2
  const s = (n: number) => `${n.toFixed(2)}s`

  return {
    '--float-dur': s(fDur),
    '--float-delay': s(-(r1 * fDur)),
    '--blink-dur': s(bDur),
    '--blink-delay': s(-(r2 * bDur)),
    '--smile-dur': s(sDur),
    '--smile-delay': s(-(r3 * sDur)),
    '--shine-dur': s(shDur),
    '--shine-delay': s(-(r5 * shDur))
  }
}

const cardStyle = computed(() => {
  const [earFrom, earTo] = EAR_CORES[props.assistente.tipo] || EAR_CORES.outro
  return {
    ...animVars(props.assistente.id || props.assistente.nome),
    '--ear-from': earFrom,
    '--ear-to': earTo
  }
})
</script>

<style scoped>
.assistente-card {
  position: relative;
  margin-top: 56px;
  border-radius: 1rem;
  border: 1px solid rgb(var(--color-border));
  background: rgb(var(--color-card));
  padding: 3.75rem 1rem 1rem;
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.04);
  transition: box-shadow .2s, transform .2s;
}
.assistente-card:hover { box-shadow: 0 10px 30px -12px rgb(80 40 180 / 0.35); transform: translateY(-2px); }

/* ════════════════ CABEÇA (flutua acima do card) ════════════════ */
.head-zone {
  position: absolute;
  top: -66px;
  left: 0;
  right: 0;
  height: 94px;
  z-index: 2;
  transition: transform 0.28s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}
.robot-head {
  position: relative;
  width: 188px;
  height: 150px;
  transform: scale(0.6);
  animation: headFloat var(--float-dur, 3.6s) ease-in-out infinite;
  animation-delay: var(--float-delay, 0s);
  filter: drop-shadow(0 12px 16px rgba(40, 28, 96, 0.18));
  transition: filter 0.3s ease;
}

/* ════════════ DORMINDO (offline): respira devagar, olhos fechados, Zzz ════════════ */
.is-off .robot-head {
  filter: grayscale(0.35) brightness(0.97) drop-shadow(0 12px 16px rgba(40, 28, 96, 0.12));
  animation: sleepBreath 4.6s ease-in-out infinite;
  animation-delay: var(--float-delay, 0s);
}
.is-off .face::after { animation: none; }
.is-off .eye {
  animation: none;
  height: 5px;
  top: 27px;
  background: transparent;
  border-bottom: 3px solid #7fd5ec;
  border-radius: 0 0 12px 12px;
  box-shadow: none;
}
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
.group:hover .zzz { opacity: 0; }
.group:hover .head-zone.is-off .robot-head {
  filter: drop-shadow(0 12px 16px rgba(40, 28, 96, 0.18));
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
  transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
  pointer-events: none;
  background: rgb(var(--color-card));
  color: rgb(var(--color-foreground));
  border: 1px solid rgb(var(--color-border));
}
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

/* ════════════════ FELIZ AO PASSAR O MOUSE (card inteiro = .group) ════════════════ */
.group:hover .head-zone {
  transform: scale(1.05) translateY(-2px);
}
.group:hover .head-zone:not(.is-off) .eye {
  animation: none;
  height: 10px;
  top: 24px;
  border-radius: 14px 14px 3px 3px;
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
  border-radius: 0 0 30px 30px;
}

/* ════════════ CHORANDO (hover na lixeira) ════════════ */
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
.group:hover:has(.btn-excluir:hover) .head-zone .eye {
  animation: none;
  height: 22px;
  top: 18px;
  border: 0;
  border-radius: 50%;
  background: #7dd3fc;
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
  border-radius: 14px 14px 0 0;
}
.group:hover:has(.btn-excluir:hover) .head-zone .tear {
  animation: tearFall 1.1s ease-in infinite;
}
.group:hover:has(.btn-excluir:hover) .head-zone .tear.right {
  animation-delay: 0.55s;
}
.group:hover:has(.btn-excluir:hover) .balao-religar {
  opacity: 0;
  pointer-events: none;
}

/* ════════════════ ANIMAÇÕES (keyframes) ════════════════ */
@keyframes headFloat {
  0%, 100% { transform: scale(0.6) translateY(0) rotate(-1deg); }
  50% { transform: scale(0.6) translateY(-7px) rotate(1.5deg); }
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
@keyframes sleepBreath {
  0%, 100% { transform: scale(0.6) translateY(0); }
  50% { transform: scale(0.604) translateY(1.5px); }
}
@keyframes zzzFloat {
  0% { opacity: 0; transform: translateY(8px) scale(0.7) rotate(-6deg); }
  20% { opacity: 0.85; }
  55% { opacity: 0.55; }
  100% { opacity: 0; transform: translateY(-18px) scale(1.05) rotate(8deg); }
}
@keyframes balaoPulse {
  0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
  50% { transform: scale(1.18); box-shadow: 0 0 0 5px rgba(16, 185, 129, 0); }
}
@keyframes charIn {
  from { opacity: 0; transform: translateY(2px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes tearFall {
  0% { opacity: 0; transform: translateY(0) scale(0.6); }
  25% { opacity: 1; }
  100% { opacity: 0; transform: translateY(28px) scale(1); }
}

/* ── Chips / badges ── */
.chip { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 700;
  letter-spacing: .04em; padding: 3px 8px; border-radius: 999px; white-space: nowrap; }
.chip-dot { width: 6px; height: 6px; border-radius: 50%; }
.chip-on { color: #059669; background: #10b98118; }
.chip-on .chip-dot { background: #10b981; box-shadow: 0 0 6px #10b981; }
.chip-off { color: rgb(var(--color-muted-fg)); background: rgb(var(--color-muted)); }
.chip-off .chip-dot { background: rgb(var(--color-muted-fg)); opacity: .5; }

.badge { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 700;
  letter-spacing: .03em; padding: 3px 8px; border-radius: 8px; border: 1px solid; }

.link-detalhes { display: inline-flex; align-items: center; gap: 3px; font-size: 12px;
  color: rgb(var(--color-muted-fg)); transition: color .15s; }
.link-detalhes:hover { color: rgb(var(--color-foreground)); }

.acao { padding: 6px; border-radius: 8px; transition: background .15s; }
.acao:hover { background: rgb(var(--color-muted)); }

/* Acessibilidade: respeita quem desativou animações no SO */
@media (prefers-reduced-motion: reduce) {
  .robot-head, .eye, .mouth, .face::after { animation: none !important; }
  .zzz .z { animation: none !important; opacity: 0.8 !important; }
  .balao-icon { animation: none !important; }
  .balao-char { animation: none !important; opacity: 1 !important; transform: none !important; }
  .tear { animation: none !important; }
}
</style>
