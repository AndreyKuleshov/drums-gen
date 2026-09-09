<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import GrooveScore from '../components/GrooveScore.vue'
import LikeButton from '../components/LikeButton.vue'
import ScoreView from '../components/ScoreView.vue'
import Stepper from '../components/Stepper.vue'
import TransportRack from '../components/TransportRack.vue'
import type { PlayEngine } from '../components/TransportRack.vue'
import { ApiError, apiFetch } from '../lib/api'
import { parseFraction, playPhrase, stopPhrase } from '../lib/audio'
import { playGroove, stopGroove } from '../lib/kit'
import { persistedRef } from '../lib/storage'
import type { Groove, Hit, Phrase } from '../types'

const tempo = persistedRef('patterns2-tempo', 100)
const bars = persistedRef('patterns2-bars', 2)
const subdivision = persistedRef('patterns2-sub', '1/16')
const singles = persistedRef('patterns2-singles', true)
const odd = persistedRef('patterns2-odd', true)
const paradiddle = persistedRef('patterns2-paradiddle', true)
// 'snare' = pure sticking; 'kit' = orchestrated across the kit (polyphonic);
// 'linear' = one line across the kit, at most one stroke at a time.
type Voicing = 'snare' | 'kit' | 'linear'
const voicing = persistedRef<Voicing>('patterns2-voicing', 'linear')
const voicings: { v: Voicing; label: string }[] = [
  { v: 'linear', label: 'Linear' },
  { v: 'snare', label: 'Snare' },
  { v: 'kit', label: 'Kit' },
]
// Subdivision doubles as a rhythm mode: '1/8'/'1/16' are uniform grids, 'mixed'
// mixes both within a bar.
const subdivisions: { value: string; label: string }[] = [
  { value: '1/8', label: '1/8' },
  { value: '1/16', label: '1/16' },
  { value: 'mixed', label: 'Mixed' },
]

const phrase = ref<Phrase | null>(null)
const groove = ref<Groove | null>(null)
const activeStep = ref<number | null>(null)
const error = ref('')
// "Alternate sticking": mirror the whole pattern's hands R<->L — same rhythm and
// orchestration, opposite lead hand — as a view transform over the current
// pattern (rendered and played mirrored).
const mirrored = ref(false)

const flip = (h: 'L' | 'R'): 'L' | 'R' => (h === 'R' ? 'L' : 'R')
const viewPhrase = computed<Phrase | null>(() => {
  const p = phrase.value
  if (p === null || !mirrored.value) return p
  return {
    ...p,
    bars: p.bars.map((b) => ({
      ...b,
      strokes: b.strokes.map((s) => ({ ...s, hand: flip(s.hand) })),
    })),
  }
})
const viewGroove = computed<Groove | null>(() => {
  const g = groove.value
  if (g === null || !mirrored.value) return g
  return {
    ...g,
    bars: g.bars.map((b) => ({
      ...b,
      hands: b.hands.map((h) => ({ ...h, hand: h.hand ? flip(h.hand) : h.hand })),
    })),
  }
})

const transport = ref<InstanceType<typeof TransportRack> | null>(null)
const canPlay = computed(() => phrase.value !== null || groove.value !== null)
const meter = { num: 4, den: 4 }

const phraseEngine: PlayEngine = {
  play: async (o) => {
    if (viewPhrase.value !== null) await playPhrase(viewPhrase.value, o)
  },
  stop: stopPhrase,
}
const grooveEngine: PlayEngine = {
  play: async (o) => {
    if (viewGroove.value !== null) await playGroove(viewGroove.value, o)
  },
  stop: stopGroove,
}
const engine = computed<PlayEngine>(() => (groove.value !== null ? grooveEngine : phraseEngine))

// Favorites: save the pattern currently on screen (mirrored or not). A Groove is
// stored as kind 'pattern' (rendered by GrooveScore in My Account), a Phrase as
// 'exercise' (ScoreView) — matching the Studio's like flow.
const cap = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)
const likePayload = computed(() => viewGroove.value ?? viewPhrase.value)
const likeMeta = computed<Record<string, unknown>>(() => ({
  kind: groove.value !== null ? 'pattern' : 'exercise',
  level: cap(voicing.value),
  meter: '4/4',
  feel: subdivision.value === 'mixed' ? 'Mixed' : subdivision.value,
  bars: bars.value,
  tempo: tempo.value,
}))

// --- Note editor: click a note to toggle accent/ghost or flip the hand. Works
// on the snare Phrase (one stroke at a time) and on kit/linear Grooves (every
// hit sounding on the clicked onset cell). Accent/ghost toggle; ghost only
// applies to the melodic voices (snare + toms).
const CELL = 1 / 32 // notation grid used by GrooveScore to key hits by onset
const MELODIC = new Set(['snare', 'tom_high', 'tom_mid', 'tom_low'])
type EditTarget =
  | { kind: 'phrase'; index: number }
  | { kind: 'groove'; bar: number; cell: number }
const editor = ref<{ target: EditTarget; x: number; y: number } | null>(null)

function noteAt(idx: number): { bar: number; i: number } | null {
  const bars = phrase.value?.bars ?? []
  let n = idx
  for (let b = 0; b < bars.length; b++) {
    if (n < bars[b].strokes.length) return { bar: b, i: n }
    n -= bars[b].strokes.length
  }
  return null
}

const cellOf = (h: Hit): number => Math.round(parseFraction(h.onset) / CELL)
function hitsAtCell(bar: number, cell: number): Hit[] {
  const b = groove.value?.bars[bar]
  return b ? b.hands.filter((h) => cellOf(h) === cell) : []
}

const editorNote = computed(() => {
  const e = editor.value
  if (e === null) return null
  if (e.target.kind === 'phrase') {
    const loc = noteAt(e.target.index)
    const s = loc ? phrase.value?.bars[loc.bar]?.strokes[loc.i] : undefined
    return s ? { accent: s.accent, ghost: s.ghost, canGhost: true, canFlip: true } : null
  }
  const hits = hitsAtCell(e.target.bar, e.target.cell)
  if (hits.length === 0) return null
  return {
    accent: hits.some((h) => h.accent),
    ghost: hits.some((h) => h.ghost),
    canGhost: hits.some((h) => MELODIC.has(h.surface)),
    canFlip: hits.some((h) => h.hand !== null),
  }
})

function onNoteClick(p: { index: number; x: number; y: number }): void {
  editor.value = { target: { kind: 'phrase', index: p.index }, x: p.x, y: p.y }
}
function onGrooveNoteClick(p: { bar: number; cell: number; x: number; y: number }): void {
  editor.value = { target: { kind: 'groove', bar: p.bar, cell: p.cell }, x: p.x, y: p.y }
}

function setPhraseNote(index: number, action: 'accent' | 'ghost' | 'flip'): void {
  const p = phrase.value
  if (p === null) return
  const loc = noteAt(index)
  if (loc === null) return
  phrase.value = {
    ...p,
    bars: p.bars.map((b, bi) =>
      bi !== loc.bar
        ? b
        : {
            ...b,
            strokes: b.strokes.map((s, si) => {
              if (si !== loc.i) return s
              if (action === 'flip') return { ...s, hand: s.hand === 'R' ? 'L' : 'R' }
              if (action === 'accent') return { ...s, accent: !s.accent, ghost: false }
              return { ...s, ghost: !s.ghost, accent: false }
            }),
          },
    ),
  }
}

function setGrooveNote(bar: number, cell: number, action: 'accent' | 'ghost' | 'flip'): void {
  const g = groove.value
  if (g === null) return
  const hits = hitsAtCell(bar, cell)
  if (hits.length === 0) return
  const nextAccent = !hits.some((h) => h.accent)
  const nextGhost = !hits.some((h) => h.ghost)
  groove.value = {
    ...g,
    bars: g.bars.map((b, bi) =>
      bi !== bar
        ? b
        : {
            ...b,
            hands: b.hands.map((h) => {
              if (cellOf(h) !== cell) return h
              if (action === 'flip') {
                return h.hand ? { ...h, hand: h.hand === 'R' ? 'L' : 'R' } : h
              }
              if (action === 'accent') {
                return { ...h, accent: nextAccent, ghost: nextAccent ? false : h.ghost }
              }
              if (!MELODIC.has(h.surface)) return h
              return { ...h, ghost: nextGhost, accent: nextGhost ? false : h.accent }
            }),
          },
    ),
  }
}

function setNote(action: 'accent' | 'ghost' | 'flip'): void {
  const e = editor.value
  if (e === null) return
  if (e.target.kind === 'phrase') setPhraseNote(e.target.index, action)
  else setGrooveNote(e.target.bar, e.target.cell, action)
}

async function generate(): Promise<void> {
  // Regenerating stops any playing pattern (same as the Studio tab), so the old
  // pattern doesn't keep sounding under the new one.
  transport.value?.stop()
  activeStep.value = null
  mirrored.value = false // a fresh pattern starts on its natural sticking
  editor.value = null
  error.value = ''
  if (!singles.value && !odd.value && !paradiddle.value) {
    error.value = 'Enable at least one block family.'
    return
  }
  const mixed = subdivision.value === 'mixed'
  const body = JSON.stringify({
    time_sig: meter,
    num_bars: bars.value,
    subdivision: mixed ? '1/16' : subdivision.value,
    mixed,
    tempo_bpm: tempo.value,
    singles: singles.value,
    odd: odd.value,
    paradiddle: paradiddle.value,
    voicing: voicing.value,
  })
  try {
    // 'snare' returns a monophonic Phrase; 'kit'/'linear' return a polyphonic
    // Groove. Fetch the shape we asked for and clear the other.
    if (voicing.value === 'snare') {
      phrase.value = await apiFetch<Phrase>('/patterns2/generate', { method: 'POST', body })
      groove.value = null
    } else {
      groove.value = await apiFetch<Groove>('/patterns2/generate', { method: 'POST', body })
      phrase.value = null
    }
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : "Couldn’t generate. Is the engine running?"
  }
}

function onGlobalKey(e: KeyboardEvent): void {
  if (e.metaKey || e.ctrlKey || e.altKey) return
  const tag = (e.target as HTMLElement | null)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (e.code === 'Space') {
    e.preventDefault()
    ;(e.target as HTMLElement | null)?.blur?.()
    transport.value?.toggle()
  } else if (e.code === 'KeyR') {
    e.preventDefault()
    transport.value?.toggleLoop()
  } else if (e.code === 'KeyC') {
    e.preventDefault()
    transport.value?.toggleClick()
  } else if (e.code === 'Enter') {
    e.preventDefault()
    void generate()
  } else if (e.code === 'Escape' && editor.value !== null) {
    editor.value = null
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onGlobalKey))
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">Patterns 2.0</span>
        </div>
        <div class="brand__meta">
          <RouterLink to="/" class="nav-link">&larr; Studio</RouterLink>
        </div>
      </header>

      <section class="screen" aria-label="Notation display">
        <div class="screen__glass">
          <LikeButton
            v-if="likePayload"
            class="screen__like"
            :payload="likePayload"
            :meta="likeMeta"
            next="/patterns2"
          />
          <GrooveScore
            v-if="viewGroove"
            :groove="viewGroove"
            :active-step="activeStep"
            label-hihat
            editable
            @note-click="onGrooveNoteClick"
          />
          <ScoreView
            v-else-if="viewPhrase"
            :phrase="viewPhrase"
            :active-step="activeStep"
            editable
            @note-click="onNoteClick"
          />
          <div v-else class="screen__empty">
            <p class="screen__empty-text">
              Toggle families and hit Generate for a sticking pattern.
            </p>
          </div>
        </div>
      </section>

      <TransportRack
        ref="transport"
        :can-play="canPlay"
        :meter="meter"
        :tempo="tempo"
        :engine="engine"
        @step="activeStep = $event"
      />

      <p v-if="error" class="formmsg formmsg--error" role="alert">{{ error }}</p>

      <form class="controls" @submit.prevent="generate">
        <div class="controls__row">
          <div class="field field--seg">
            <span class="field__label">Families</span>
            <div class="segment" role="group" aria-label="Block families">
              <button
                type="button"
                :aria-pressed="singles"
                :class="['segment__btn', { 'is-active': singles }]"
                @click="singles = !singles"
              >
                Singles
              </button>
              <button
                type="button"
                :aria-pressed="odd"
                :class="['segment__btn', { 'is-active': odd }]"
                @click="odd = !odd"
              >
                Odd 3/5/7
              </button>
              <button
                type="button"
                :aria-pressed="paradiddle"
                :class="['segment__btn', { 'is-active': paradiddle }]"
                @click="paradiddle = !paradiddle"
              >
                Paradiddle
              </button>
            </div>
          </div>

          <div class="field field--seg">
            <span class="field__label">Voicing</span>
            <div class="segment" role="radiogroup" aria-label="Voicing">
              <button
                v-for="o in voicings"
                :key="o.v"
                type="button"
                role="radio"
                :aria-checked="voicing === o.v"
                :class="['segment__btn', { 'is-active': voicing === o.v }]"
                @click="voicing = o.v"
              >
                {{ o.label }}
              </button>
            </div>
          </div>

          <div class="field field--seg">
            <span class="field__label">Subdivision</span>
            <div class="segment" role="radiogroup" aria-label="Subdivision">
              <button
                v-for="s in subdivisions"
                :key="s.value"
                type="button"
                role="radio"
                :aria-checked="subdivision === s.value"
                :class="['segment__btn', { 'is-active': subdivision === s.value }]"
                @click="subdivision = s.value"
              >
                {{ s.label }}
              </button>
            </div>
          </div>
        </div>

        <div class="controls__row controls__row--foot">
          <div class="field field--fixed">
            <span class="field__label">Bars</span>
            <Stepper v-model="bars" :min="1" :max="16" label="Number of bars" />
          </div>

          <div class="field field--fixed">
            <span class="field__label">Tempo</span>
            <div class="inline">
              <Stepper v-model="tempo" :min="30" :max="300" :step="1" label="Tempo (BPM)" />
              <span class="inline__sep">bpm</span>
            </div>
          </div>

          <button
            type="button"
            class="altstick"
            :class="{ 'is-active': mirrored }"
            :disabled="!canPlay"
            :aria-pressed="mirrored"
            data-tip="Mirror the whole sticking R↔L"
            @click="mirrored = !mirrored"
          >
            <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
              <path
                d="M8 7h9M8 7l3-3M8 7l3 3M16 17H7M16 17l-3-3M16 17l-3 3"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            Alt sticking
          </button>

          <button
            class="btn-primary controls__go"
            type="submit"
            data-test="generate"
            data-tip="Generate (Enter)"
          >
            Generate
          </button>
        </div>
      </form>
    </div>
  </main>

  <Teleport to="body">
    <div v-if="editor" class="noteedit__backdrop" @click="editor = null" />
    <div
      v-if="editor"
      class="noteedit"
      :style="{ left: editor.x + 'px', top: editor.y + 'px' }"
      role="menu"
    >
      <button
        type="button"
        :class="{ on: editorNote?.accent }"
        @click="setNote('accent')"
      >
        Accent
      </button>
      <button
        type="button"
        :class="{ on: editorNote?.ghost }"
        :disabled="editorNote !== null && !editorNote.canGhost"
        @click="setNote('ghost')"
      >
        Ghost
      </button>
      <button
        type="button"
        :disabled="editorNote !== null && !editorNote.canFlip"
        @click="setNote('flip')"
      >
        Flip R/L
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
/* Controls adopt the Studio's control-panel language: labelled fields with
   segmented toggles and steppers, so both generators read as one system. */
.controls {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 4px;
  padding: 18px;
  border-radius: var(--r-lg);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  box-shadow: var(--shadow-1), inset 0 1px 0 rgba(239, 231, 216, 0.04);
}

.controls__row {
  display: flex;
  flex-wrap: wrap;
  gap: 18px 22px;
}

.controls__row--foot {
  align-items: flex-end;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field--fixed {
  flex: 0 0 auto;
}

/* Basis is a min-width so segments stretch to fill the row; a two-option
   toggle needs less room than the three-option Families group. */
.field--seg {
  flex: 1 1 260px;
}


.field__label {
  font-family: var(--font-mono);
  font-size: 0.66rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.segment {
  display: flex;
  width: 100%;
  padding: 4px;
  gap: 4px;
  background: #100e0c;
  border: 1px solid var(--edge);
  border-radius: var(--r-md);
  box-shadow: var(--inset);
}

.segment__btn {
  flex: 1 1 auto;
  padding: 9px 14px;
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text-dim);
  font-family: var(--font-ui);
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.segment__btn:hover {
  color: var(--text);
}

.segment__btn.is-active {
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  border-color: var(--edge);
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), 0 0 0 1px rgba(255, 157, 60, 0.18);
}

.inline {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.inline__sep {
  color: var(--text-faint);
  font-family: var(--font-mono);
  font-size: 0.82rem;
}

.controls__go {
  margin-left: auto;
  min-width: 160px;
}

/* "Alternate sticking" toggle — mirrors the current pattern's hands R<->L. */
.altstick {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 13px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition:
    color 0.15s ease,
    box-shadow 0.18s ease;
}

.altstick:hover:not(:disabled) {
  color: var(--text);
}

.altstick.is-active {
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), inset 0 0 0 1px rgba(255, 157, 60, 0.3);
}

.altstick:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.screen {
  border-radius: var(--r-lg);
  padding: 10px;
  background: linear-gradient(180deg, #0f0d0b, #171310);
  border: 1px solid var(--edge);
}
.screen__glass {
  position: relative;
  min-height: 200px;
  border-radius: var(--r-md);
  background: linear-gradient(180deg, #fbf6ec, var(--screen));
  border: 1px solid var(--screen-edge);
  display: flex;
  align-items: center;
}

.screen__like {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 4;
}
.screen__empty {
  width: 100%;
  padding: 40px 24px;
  text-align: center;
}
.screen__empty-text {
  color: #6b6252;
}
.formmsg--error {
  color: var(--danger);
  font-size: 0.88rem;
  margin: 0;
}

@media (max-width: 560px) {
  .controls {
    padding: 14px;
    gap: 14px;
  }
  .controls__row {
    gap: 14px 16px;
  }
  .field--seg {
    flex: 1 1 100%;
  }
  .segment {
    flex-wrap: wrap;
  }
  .segment__btn {
    flex: 1 1 42%;
    padding: 9px 10px;
    font-size: 0.85rem;
  }
  .controls__go {
    margin-left: 0;
    width: 100%;
  }
}

/* Note editor popover — click a note to toggle accent/ghost or flip the hand.
   Teleported to <body>; the scoped id rides along so these styles apply. */
.noteedit__backdrop {
  position: fixed;
  inset: 0;
  z-index: 70;
}

.noteedit {
  position: fixed;
  z-index: 71;
  transform: translate(-50%, calc(-100% - 12px));
  display: flex;
  gap: 4px;
  padding: 5px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  box-shadow: var(--shadow-2), 0 0 24px -8px var(--amber-glow);
}

.noteedit button {
  padding: 7px 11px;
  border-radius: var(--r-sm);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  white-space: nowrap;
  cursor: pointer;
  transition:
    color 0.14s ease,
    background 0.14s ease;
}

.noteedit button:hover {
  color: var(--text);
  background: #100e0c;
}

.noteedit button.on {
  color: var(--amber-bright);
  box-shadow: inset 0 0 0 1px rgba(255, 157, 60, 0.3);
}

.noteedit button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.noteedit button:disabled:hover {
  color: var(--text-dim);
  background: transparent;
}
</style>
