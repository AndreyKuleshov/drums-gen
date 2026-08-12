<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AuthNav from '../components/AuthNav.vue'
import GrooveScore from '../components/GrooveScore.vue'
import LikeButton from '../components/LikeButton.vue'
import ModeSwitch from '../components/ModeSwitch.vue'
import ScoreView from '../components/ScoreView.vue'
import StudioControls from '../components/StudioControls.vue'
import type { StudioForm } from '../components/StudioControls.vue'
import TransportRack from '../components/TransportRack.vue'
import type { PlayEngine } from '../components/TransportRack.vue'
import { apiFetch } from '../lib/api'
import { playPhrase, stopPhrase } from '../lib/audio'
import { playGroove, stopGroove } from '../lib/kit'
import { takePendingGroove, takePendingPhrase } from '../lib/loadedPattern'
import { persistedRef } from '../lib/storage'
import type { Groove, Phrase } from '../types'

// One page, one control set. `mode` (the single distinguishing parameter) lives
// in the header switch and just flips reactive state — no separate route.
const mode = persistedRef<'groove' | 'exercise'>('studio-mode', 'groove')
const tempo = persistedRef('studio-tempo', 100)

const activeStep = ref<number | null>(null)
const booting = ref(false)
const error = ref('')
let bootTimer: ReturnType<typeof setTimeout> | null = null

const groove = ref<Groove | null>(null)
const phrase = ref<Phrase | null>(null)
const lastForm = ref<StudioForm | null>(null)

const transport = ref<InstanceType<typeof TransportRack> | null>(null)
const controls = ref<InstanceType<typeof StudioControls> | null>(null)

const canPlay = computed(() =>
  mode.value === 'groove' ? groove.value !== null : phrase.value !== null,
)
const meter = computed(() => {
  const ts = mode.value === 'groove' ? groove.value?.bars[0]?.time_sig : phrase.value?.time_sig
  return ts ?? { num: 4, den: 4 }
})

const grooveEngine: PlayEngine = {
  play: async (o) => {
    if (groove.value !== null) await playGroove(groove.value, o)
  },
  stop: stopGroove,
}
const phraseEngine: PlayEngine = {
  play: async (o) => {
    if (phrase.value !== null) await playPhrase(phrase.value, o)
  },
  stop: stopPhrase,
}
const engine = computed<PlayEngine>(() =>
  mode.value === 'groove' ? grooveEngine : phraseEngine,
)

const cap = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)
// Triplet turns the base subdivision into its triplet grid (1/8→1/12, 1/16→1/24).
const TRIPLET_OF: Record<string, string> = { '1/8': '1/12', '1/16': '1/24' }
const gridOf = (form: StudioForm): string =>
  form.feel === 'triplet' ? (TRIPLET_OF[form.base] ?? form.base) : form.base

function bootScreen(): void {
  transport.value?.stop()
  activeStep.value = null
  if (bootTimer !== null) clearTimeout(bootTimer)
  requestAnimationFrame(() => {
    booting.value = true
    bootTimer = setTimeout(() => (booting.value = false), 600)
  })
}

// The one control set feeds both generators; only the request shape differs.
async function generate(form: StudioForm): Promise<void> {
  error.value = ''
  lastForm.value = form
  try {
    if (mode.value === 'exercise') {
      const next = await apiFetch<Phrase>('/generate', {
        method: 'POST',
        body: JSON.stringify({
          time_sig: { num: form.num, den: form.den },
          num_bars: form.num_bars,
          min_subdivision: gridOf(form),
          tempo_bpm: tempo.value,
          accent_mode: form.accents,
          mixed: form.feel === 'mixed',
          authentic: form.feel === 'authentic',
          difficulty: form.difficulty,
        }),
      })
      phrase.value = next
    } else {
      const next = await apiFetch<Groove>('/pattern/generate', {
        method: 'POST',
        body: JSON.stringify({
          time_sig: { num: form.num, den: form.den },
          num_bars: form.num_bars,
          tempo_bpm: tempo.value,
          difficulty: form.difficulty,
          style: form.style,
          hands: form.hands,
          subdivision: form.base,
          feel: form.feel,
        }),
      })
      groove.value = next
    }
    bootScreen()
  } catch {
    error.value = 'Couldn’t generate. Is the engine running?'
  }
}

// Summary plate — derived from the last generated form + mode + result.
const spec = computed<{ label: string; value: string | number; small?: string }[]>(() => {
  const f = lastForm.value
  if (f === null) return []
  const level = cap(f.difficulty === 'pro' ? 'advanced' : f.difficulty)
  const meterStr = `${f.num}/${f.den}`
  if (mode.value === 'groove') {
    const rows: { label: string; value: string | number; small?: string }[] = [
      { label: 'Level', value: level },
      { label: 'Meter', value: meterStr },
      { label: 'Type', value: cap(f.style) },
      { label: 'Bars', value: f.num_bars },
    ]
    if (f.style !== 'fill') rows.push({ label: 'Hands', value: cap(f.hands) })
    rows.push({ label: 'Tempo', value: tempo.value, small: 'bpm' })
    return rows
  }
  const notes = phrase.value?.bars.reduce((n, b) => n + b.strokes.length, 0) ?? '—'
  return [
    { label: 'Level', value: level },
    { label: 'Meter', value: meterStr },
    { label: 'Grid', value: gridOf(f) },
    { label: 'Feel', value: cap(f.feel) },
    { label: 'Accents', value: cap(f.accents) },
    { label: 'Bars', value: f.num_bars },
    { label: 'Notes', value: notes },
    { label: 'Tempo', value: tempo.value, small: 'bpm' },
  ]
})

const likePayload = computed(() => (mode.value === 'groove' ? groove.value : phrase.value))
const likeMeta = computed<Record<string, unknown>>(() => {
  const f = lastForm.value
  const level = f === null ? '—' : cap(f.difficulty === 'pro' ? 'advanced' : f.difficulty)
  if (mode.value === 'groove') {
    return {
      kind: 'pattern',
      level,
      meter: f ? `${f.num}/${f.den}` : '—',
      type: f ? cap(f.style) : '—',
      bars: f?.num_bars,
      hands: f && f.style !== 'fill' ? cap(f.hands) : '—',
      tempo: tempo.value,
    }
  }
  return {
    kind: 'exercise',
    level,
    meter: f ? `${f.num}/${f.den}` : '—',
    grid: f ? gridOf(f) : '—',
    feel: f ? cap(f.feel) : '—',
    accents: f ? cap(f.accents) : '—',
    bars: f?.num_bars,
    notes: phrase.value?.bars.reduce((n, b) => n + b.strokes.length, 0),
    tempo: tempo.value,
  }
})

const brandName = computed(() =>
  mode.value === 'groove' ? 'Groove Pattern' : 'Rudiment Exercises',
)
const emptyText = computed(() =>
  mode.value === 'groove'
    ? 'Pick a level and hit Generate for a kick / snare / hi-hat groove.'
    : 'Set the meter and hit Generate to score a rudiment phrase.',
)

function onModeChange(): void {
  transport.value?.stop()
  activeStep.value = null
}

// Keyboard shortcuts: Space = Play/Stop, R = Loop, C = Click, Enter = Generate.
function onGlobalKey(e: KeyboardEvent): void {
  if (e.metaKey || e.ctrlKey || e.altKey) return
  const tag = (e.target as HTMLElement | null)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (e.code === 'Space') {
    e.preventDefault()
    ;(e.target as HTMLElement | null)?.blur?.() // avoid a focused button's keyup click
    transport.value?.toggle()
  } else if (e.code === 'KeyR') {
    e.preventDefault()
    transport.value?.toggleLoop()
  } else if (e.code === 'KeyC') {
    e.preventDefault()
    transport.value?.toggleClick()
  } else if (e.code === 'Enter') {
    e.preventDefault()
    controls.value?.submit()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onGlobalKey)
  const g = takePendingGroove()
  if (g !== null) {
    mode.value = 'groove'
    groove.value = g
  }
  const p = takePendingPhrase()
  if (p !== null) {
    mode.value = 'exercise'
    phrase.value = p
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onGlobalKey))
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">{{ brandName }}</span>
        </div>
        <div class="brand__meta">
          <ModeSwitch v-model="mode" @update:model-value="onModeChange" />
          <RouterLink to="/shortcuts" class="nav-link" title="Keyboard shortcuts">⌨ Shortcuts</RouterLink>
          <RouterLink to="/rudiments" class="nav-link">Rudiments &rarr;</RouterLink>
          <AuthNav />
          <span class="led led--on" aria-hidden="true" />
        </div>
      </header>

      <section class="screen" aria-label="Notation display">
        <div class="screen__glass" :class="{ 'screen__glass--boot': booting }">
          <LikeButton
            v-if="likePayload"
            class="screen__like"
            :payload="likePayload"
            :meta="likeMeta"
            next="/"
          />
          <GrooveScore
            v-if="mode === 'groove' && groove"
            :groove="groove"
            :active-step="activeStep"
          />
          <ScoreView
            v-else-if="mode === 'exercise' && phrase"
            :phrase="phrase"
            :active-step="activeStep"
          />
          <div v-else class="screen__empty">
            <span class="screen__empty-glyph" aria-hidden="true">&#9834;</span>
            <p class="screen__empty-text">{{ emptyText }}</p>
          </div>
        </div>

        <dl v-if="spec.length" class="specplate" aria-label="Pattern summary">
          <div v-for="row in spec" :key="row.label">
            <dt>{{ row.label }}</dt>
            <dd>{{ row.value }}<small v-if="row.small">{{ row.small }}</small></dd>
          </div>
        </dl>
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
      <StudioControls ref="controls" :mode="mode" v-model:tempo="tempo" @submit="generate" />
    </div>
  </main>
</template>

<style scoped>
.screen {
  border-radius: var(--r-lg);
  padding: 10px;
  background: linear-gradient(180deg, #0f0d0b, #171310);
  border: 1px solid var(--edge);
  box-shadow: var(--inset);
}

.screen__glass {
  position: relative;
  min-height: 220px;
  border-radius: var(--r-md);
  background: linear-gradient(180deg, #fbf6ec, var(--screen));
  border: 1px solid var(--screen-edge);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.4),
    inset 0 2px 14px rgba(120, 96, 60, 0.18),
    0 0 22px -6px var(--amber-glow);
  overflow: hidden;
  display: flex;
  align-items: center;
}

.screen__like {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 4;
}

.screen__glass--boot {
  animation: screen-boot 550ms cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes screen-boot {
  0% {
    box-shadow:
      inset 0 0 0 1px rgba(255, 255, 255, 0.4),
      inset 0 2px 14px rgba(120, 96, 60, 0.18),
      0 0 46px 2px var(--amber-glow);
    filter: brightness(1.05);
  }
  100% {
    box-shadow:
      inset 0 0 0 1px rgba(255, 255, 255, 0.4),
      inset 0 2px 14px rgba(120, 96, 60, 0.18),
      0 0 22px -6px var(--amber-glow);
    filter: brightness(1);
  }
}

.specplate {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 22px;
  margin: 10px 4px 2px;
  padding: 8px 4px 0;
}

.specplate > div {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.specplate dt {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.specplate dd {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.86rem;
  font-weight: 500;
  color: var(--amber-bright);
}

.specplate dd small {
  margin-left: 3px;
  font-size: 0.58rem;
  color: var(--text-faint);
  letter-spacing: 0.08em;
}

.screen__empty {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 24px;
  text-align: center;
}

.screen__empty-glyph {
  font-size: 2.4rem;
  color: #b9ac93;
  line-height: 1;
}

.screen__empty-text {
  max-width: 42ch;
  color: #6b6252;
  font-size: 0.95rem;
}

.formmsg--error {
  color: var(--danger);
  font-size: 0.88rem;
  margin: 0;
}
</style>
