<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AuthNav from '../components/AuthNav.vue'
import ModeSwitch from '../components/ModeSwitch.vue'
import NotationScreen from '../components/NotationScreen.vue'
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
      view: 'studio', // which studio saved it — favorites reopen here
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
    view: 'studio',
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

// The generation form, as the reproducible params stored with a rating.
const ratingParams = computed<Record<string, unknown>>(() => ({ ...(lastForm.value ?? {}) }))

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
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKey)
  if (bootTimer !== null) clearTimeout(bootTimer)
})
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
          <RouterLink to="/patterns2" class="nav-link">Patterns 2.0 &rarr;</RouterLink>
          <AuthNav />
          <span class="led led--on" aria-hidden="true" />
        </div>
      </header>

      <NotationScreen
        :groove="mode === 'groove' ? groove : null"
        :phrase="mode === 'exercise' ? phrase : null"
        :active-step="activeStep"
        :empty-text="emptyText"
        :boot="booting"
        :rate="likePayload"
        :rate-kind="mode === 'groove' ? 'pattern' : 'exercise'"
        :rate-params="ratingParams"
        :rate-seed="null"
        :rate-meta="likeMeta"
      >
        <template #below>
          <dl v-if="spec.length" class="specplate" aria-label="Pattern summary">
            <div v-for="row in spec" :key="row.label">
              <dt>{{ row.label }}</dt>
              <dd>{{ row.value }}<small v-if="row.small">{{ row.small }}</small></dd>
            </div>
          </dl>
        </template>
      </NotationScreen>

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

.formmsg--error {
  color: var(--danger);
  font-size: 0.88rem;
  margin: 0;
}
</style>
