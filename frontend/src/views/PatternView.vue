<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import AuthNav from '../components/AuthNav.vue'
import GrooveScore from '../components/GrooveScore.vue'
import LikeButton from '../components/LikeButton.vue'
import ModeSwitch from '../components/ModeSwitch.vue'
import Stepper from '../components/Stepper.vue'
import { apiFetch } from '../lib/api'
import { playGroove, setGrooveLoop, setGrooveTempo, stopGroove } from '../lib/kit'
import { takePendingGroove } from '../lib/loadedPattern'
import { loadSetting, persistedRef, saveSetting } from '../lib/storage'
import type { Groove } from '../types'

const groove = ref<Groove | null>(null)
const activeStep = ref<number | null>(null)
const playing = ref(false)
const loop = persistedRef('pattern-loop', false)
const tempo = persistedRef('pattern-tempo', 100)
const error = ref('')

const dens = [4, 8, 16]
const difficulties = [
  { value: 'beginner', label: 'Beginner', hint: 'Kick on 1 & 3, eighth-note hi-hat, backbeat snare' },
  { value: 'mid', label: 'Mid', hint: 'Syncopated kick, ghost notes, an open hi-hat' },
  { value: 'pro', label: 'Advanced', hint: 'Double-pedal kick, 16th-note hi-hat inserts' },
]

const defaults = { num: 4, den: 4, num_bars: 2, difficulty: 'beginner' }
const form = reactive({ ...defaults, ...loadSetting('pattern-form', {}) })

const cap = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)
const difficultyLabel = computed(
  () => difficulties.find((d) => d.value === form.difficulty)?.label ?? cap(form.difficulty),
)

const likeMeta = computed<Record<string, unknown>>(() => ({
  kind: 'pattern',
  level: difficultyLabel.value,
  meter: `${form.num}/${form.den}`,
  bars: form.num_bars,
  tempo: tempo.value,
}))

async function generate(): Promise<void> {
  error.value = ''
  stop()
  saveSetting('pattern-form', { ...form })
  try {
    groove.value = await apiFetch<Groove>('/pattern/generate', {
      method: 'POST',
      body: JSON.stringify({
        time_sig: { num: form.num, den: form.den },
        num_bars: form.num_bars,
        tempo_bpm: tempo.value,
        difficulty: form.difficulty,
      }),
    })
  } catch {
    error.value = 'Couldn’t generate a pattern. Is the engine running?'
  }
}

async function play(): Promise<void> {
  if (groove.value === null) return
  playing.value = true
  await playGroove(groove.value, {
    loop: loop.value,
    tempoBpm: tempo.value,
    onStep: (i) => (activeStep.value = i),
    onEnd: () => {
      playing.value = false
      activeStep.value = null
    },
  })
}

function stop(): void {
  stopGroove()
  playing.value = false
  activeStep.value = null
}

function togglePlay(): void {
  if (playing.value) stop()
  else void play()
}

watch(tempo, (v) => {
  if (playing.value) setGrooveTempo(v)
})
watch(loop, (v) => {
  if (playing.value) setGrooveLoop(v)
})

onMounted(() => {
  const pending = takePendingGroove()
  if (pending !== null) groove.value = pending
})

onBeforeUnmount(stop)
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">Groove Pattern</span>
        </div>
        <div class="brand__meta">
          <ModeSwitch />
          <RouterLink to="/rudiments" class="nav-link">Rudiments &rarr;</RouterLink>
          <AuthNav />
          <span class="led led--on" aria-hidden="true" />
        </div>
      </header>

      <section class="screen" aria-label="Notation display">
        <div class="screen__glass">
          <LikeButton
            v-if="groove"
            class="screen__like"
            :payload="groove"
            :meta="likeMeta"
            next="/"
          />
          <GrooveScore v-if="groove" :groove="groove" :active-step="activeStep" />
          <div v-else class="screen__empty">
            <span class="screen__empty-glyph" aria-hidden="true">&#9834;</span>
            <p class="screen__empty-text">
              Pick a level and hit <strong>Generate</strong> for a kick / snare / hi-hat groove.
            </p>
          </div>
        </div>

        <dl v-if="groove" class="specplate" aria-label="Pattern summary">
          <div><dt>Level</dt><dd>{{ difficultyLabel }}</dd></div>
          <div><dt>Meter</dt><dd>{{ form.num }}/{{ form.den }}</dd></div>
          <div><dt>Bars</dt><dd>{{ form.num_bars }}</dd></div>
          <div><dt>Tempo</dt><dd>{{ tempo }}<small>bpm</small></dd></div>
        </dl>
      </section>

      <div class="transport">
        <button
          class="transport__play"
          type="button"
          :disabled="!groove"
          :aria-label="playing ? 'Stop' : 'Play'"
          @click="togglePlay"
        >
          <span v-if="playing" aria-hidden="true">&#9632;</span>
          <span v-else aria-hidden="true">&#9654;</span>
        </button>
        <button
          class="transport__toggle"
          type="button"
          :class="{ 'transport__toggle--on': loop }"
          :aria-pressed="loop"
          @click="loop = !loop"
        >
          Loop
        </button>
        <label class="transport__tempo">
          Tempo
          <Stepper v-model="tempo" :min="30" :max="300" :step="1" label="Tempo (BPM)" />
        </label>
      </div>

      <form class="patternform" @submit.prevent="generate">
        <p v-if="error" class="formmsg formmsg--error" role="alert">{{ error }}</p>

        <div class="patternform__grid">
          <div class="field">
            <span class="field__label">Meter</span>
            <div class="meter">
              <Stepper v-model="form.num" :min="1" :max="16" label="Beats per bar" />
              <span class="meter__slash">/</span>
              <div class="seg seg--sm">
                <button
                  v-for="d in dens"
                  :key="d"
                  type="button"
                  class="seg__opt"
                  :class="{ 'seg__opt--on': form.den === d }"
                  @click="form.den = d"
                >
                  {{ d }}
                </button>
              </div>
            </div>
          </div>

          <div class="field">
            <span class="field__label">Bars</span>
            <Stepper v-model="form.num_bars" :min="1" :max="8" label="Number of bars" />
          </div>
        </div>

        <div class="field">
          <span class="field__label">Difficulty</span>
          <div class="seg">
            <button
              v-for="d in difficulties"
              :key="d.value"
              type="button"
              class="seg__opt"
              :class="{ 'seg__opt--on': form.difficulty === d.value }"
              @click="form.difficulty = d.value"
            >
              {{ d.label }}
            </button>
          </div>
          <p class="field__hint">
            {{ difficulties.find((d) => d.value === form.difficulty)?.hint }}
          </p>
        </div>

        <button class="btn-primary patternform__go" type="submit">Generate</button>
      </form>
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
  min-height: 200px;
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

.screen__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 40px 20px;
  color: #8a7256;
}

.screen__empty-glyph {
  font-size: 2rem;
}

.screen__empty-text {
  margin: 0;
  font-size: 0.95rem;
}

.specplate {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 22px;
  margin: 12px 2px 0;
  font-family: var(--font-mono);
  font-size: 0.72rem;
}

.specplate div {
  display: flex;
  gap: 6px;
}

.specplate dt {
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.specplate dd {
  margin: 0;
  color: var(--amber-bright);
}

.specplate small {
  color: var(--text-faint);
  margin-left: 2px;
}

.transport {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: var(--r-lg);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  box-shadow: var(--shadow-1), var(--inset);
}

.transport__play {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  flex: none;
  border-radius: 50%;
  border: 1px solid var(--amber-dim);
  background: linear-gradient(180deg, var(--amber), var(--amber-dim));
  color: #1a1206;
  font-size: 1.1rem;
  cursor: pointer;
  box-shadow: var(--shadow-1), 0 0 18px -6px var(--amber-glow);
}

.transport__play:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  filter: grayscale(0.5);
}

.transport__toggle {
  min-height: 40px;
  padding: 8px 16px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.66rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  cursor: pointer;
}

.transport__toggle--on {
  color: var(--amber-bright);
  border-color: var(--amber-dim);
}

.transport__tempo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 0.66rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.patternform {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  border-radius: var(--r-lg);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  box-shadow: var(--shadow-1), inset 0 1px 0 rgba(239, 231, 216, 0.04);
}

.patternform__grid {
  display: flex;
  flex-wrap: wrap;
  gap: 22px;
}

.meter {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.meter__slash {
  color: var(--text-faint);
  font-family: var(--font-mono);
}

.seg {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: #100e0c;
  box-shadow: var(--inset);
  flex-wrap: wrap;
}

.seg__opt {
  padding: 8px 16px;
  border-radius: var(--r-sm);
  border: none;
  background: transparent;
  color: var(--text-dim);
  font-family: var(--font-ui);
  font-size: 0.9rem;
  cursor: pointer;
  transition: color 0.15s ease;
}

.seg--sm .seg__opt {
  padding: 8px 12px;
  font-family: var(--font-mono);
}

.seg__opt--on {
  color: #1a1206;
  background: linear-gradient(180deg, var(--amber), var(--amber-dim));
}

.patternform__go {
  align-self: flex-end;
  min-width: 160px;
}
</style>
