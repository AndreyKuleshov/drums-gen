<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

import { loadSetting, saveSetting } from '../lib/storage'
import Stepper from './Stepper.vue'

// Common controls are shared; a few are mode-specific (Subdivision/Feel/Accents
// for Exercises; Type/Hands for Pattern). `mode` (the distinguishing parameter)
// lives in the header switch.
const props = defineProps<{ mode: 'groove' | 'exercise' }>()
const tempo = defineModel<number>('tempo', { default: 100 })
const emit = defineEmits<{ (e: 'submit', form: StudioForm): void }>()

export interface StudioForm {
  num: number
  den: number
  num_bars: number
  base: string
  difficulty: string
  feel: string
  accents: string
  style: string
  hands: string
}

const defaults: StudioForm = {
  num: 4,
  den: 4,
  num_bars: 4,
  base: '1/16',
  difficulty: 'beginner',
  feel: 'straight',
  accents: 'metric',
  style: 'groove',
  hands: 'straight',
}
const form = reactive<StudioForm>({ ...defaults, ...loadSetting('studio-form', {}) })
form.den = 4 // meter is always N/4

// Fills top out at 4 bars; everything else at 8.
const isFill = computed(() => props.mode === 'groove' && form.style === 'fill')
const maxBars = computed(() => (isFill.value ? 4 : 8))
watch(maxBars, (m) => {
  if (form.num_bars > m) form.num_bars = m
})
// Default bar count per mode: Fill = 1 bar, everything else = 4. Applied when the
// mode/type changes (not on mount, so a returning session keeps its last value).
watch(isFill, (fill) => {
  form.num_bars = fill ? 1 : 4
})

interface Opt {
  value: string
  label: string
  hint?: string
}
const bases: Opt[] = [
  { value: '1/8', label: '1/8' },
  { value: '1/16', label: '1/16' },
]
const difficulties: Opt[] = [
  { value: 'beginner', label: 'Beginner', hint: 'Simplest patterns — single/double strokes, the classic beat' },
  { value: 'mid', label: 'Mid', hint: 'More syncopation — longer paradiddles and rolls' },
  { value: 'pro', label: 'Advanced', hint: 'Full vocabulary — flams, drags, double-pedal kick' },
]
const feels: Opt[] = [
  { value: 'straight', label: 'Straight', hint: 'Even notes at the chosen subdivision' },
  { value: 'triplet', label: 'Triplet', hint: 'Triplet grid (three notes per beat)' },
  { value: 'mixed', label: 'Mixed', hint: 'Mix of quarters, eighths and sixteenths per beat' },
  { value: 'authentic', label: 'Authentic', hint: "Rudiments play their real rhythm — a roll's release is longer" },
]
const accentModes: Opt[] = [
  { value: 'rudiment', label: 'Rudiment', hint: 'Accents where the rudiment places them' },
  { value: 'metric', label: 'Metric', hint: 'Accents on the strong beats of the bar' },
  { value: 'both', label: 'Both', hint: 'Rudiment accents plus the metric beats' },
]
const styleOpts: Opt[] = [
  { value: 'groove', label: 'Groove', hint: 'A repeating kick / snare / hi-hat beat' },
  { value: 'fill', label: 'Fill', hint: 'A 1–4 bar fill across snare and toms — a “fill of the day”' },
  { value: 'phrase', label: 'Phrase', hint: 'Groove with a fill on every 4th bar (3 + 1)' },
]
const handsOpts: Opt[] = [
  { value: 'straight', label: 'Straight', hint: 'Steady hi-hat with a backbeat snare' },
  { value: 'rudiment', label: 'Rudiment', hint: 'Orchestrate a rudiment across hi-hat and snare' },
]

const hintOf = (opts: Opt[], value: string): string => opts.find((o) => o.value === value)?.hint ?? ''
const difficultyHint = computed(() => hintOf(difficulties, form.difficulty))
const feelHint = computed(() => hintOf(feels, form.feel))
const accentHint = computed(() => hintOf(accentModes, form.accents))
const styleHint = computed(() => hintOf(styleOpts, form.style))
const handsHint = computed(() => hintOf(handsOpts, form.hands))

const showHands = computed(() => props.mode === 'groove' && form.style !== 'fill')

// Triplet grooves need triplet notation (not built yet) — disabled in Pattern.
const tripletDisabled = (value: string): boolean =>
  props.mode === 'groove' && value === 'triplet'
watch(
  () => props.mode,
  (m) => {
    if (m === 'groove' && form.feel === 'triplet') form.feel = 'straight'
  },
  { immediate: true },
)

function submit(): void {
  saveSetting('studio-form', { ...form })
  emit('submit', { ...form })
}
defineExpose({ submit })
</script>

<template>
  <form class="controls" @submit.prevent="submit">
    <div class="controls__row controls__row--top">
      <div class="field field--fixed">
        <span class="field__label">Meter</span>
        <div class="inline">
          <Stepper v-model="form.num" :min="1" :max="16" label="Beats per bar" />
          <span class="inline__sep">/</span>
          <span class="inline__den">4</span>
        </div>
      </div>

      <div class="field field--fixed">
        <span class="field__label">Bars</span>
        <Stepper v-model="form.num_bars" :min="1" :max="maxBars" label="Number of bars" />
      </div>

      <div class="field field--fixed">
        <span class="field__label">Tempo</span>
        <div class="inline">
          <Stepper v-model="tempo" :min="30" :max="300" :step="1" label="Tempo (BPM)" />
          <span class="inline__sep">bpm</span>
        </div>
      </div>

      <div class="field field--seg">
        <span class="field__label">Subdivision</span>
        <div class="segment" role="radiogroup" aria-label="Subdivision">
          <button
            v-for="o in bases"
            :key="o.value"
            type="button"
            role="radio"
            :aria-checked="form.base === o.value"
            :class="['segment__btn', { 'is-active': form.base === o.value }]"
            @click="form.base = o.value"
          >
            {{ o.label }}
          </button>
        </div>
      </div>
    </div>

    <div class="controls__row">
      <div class="field field--seg">
        <span class="field__label">Difficulty</span>
        <div class="segment" role="radiogroup" aria-label="Difficulty">
          <button
            v-for="o in difficulties"
            :key="o.value"
            type="button"
            role="radio"
            :aria-checked="form.difficulty === o.value"
            :title="o.hint"
            :class="['segment__btn', { 'is-active': form.difficulty === o.value }]"
            @click="form.difficulty = o.value"
          >
            {{ o.label }}
          </button>
        </div>
        <p class="field__hint">{{ difficultyHint }}</p>
      </div>

      <div class="field field--seg">
        <span class="field__label">Feel</span>
        <div class="segment" role="radiogroup" aria-label="Rhythmic feel">
          <button
            v-for="o in feels"
            :key="o.value"
            type="button"
            role="radio"
            :aria-checked="form.feel === o.value"
            :aria-disabled="tripletDisabled(o.value) || undefined"
            :data-tip="tripletDisabled(o.value) ? 'Coming soon' : undefined"
            :data-tip-pos="tripletDisabled(o.value) ? 'below' : undefined"
            :class="[
              'segment__btn',
              { 'is-active': form.feel === o.value, 'is-disabled': tripletDisabled(o.value) },
            ]"
            @click="tripletDisabled(o.value) || (form.feel = o.value)"
          >
            {{ o.label }}
          </button>
        </div>
        <p class="field__hint">{{ feelHint }}</p>
      </div>

      <div v-if="mode === 'groove'" class="field field--seg">
        <span class="field__label">Type</span>
        <div class="segment" role="radiogroup" aria-label="Pattern type">
          <button
            v-for="o in styleOpts"
            :key="o.value"
            type="button"
            role="radio"
            :aria-checked="form.style === o.value"
            :title="o.hint"
            :class="['segment__btn', { 'is-active': form.style === o.value }]"
            @click="form.style = o.value"
          >
            {{ o.label }}
          </button>
        </div>
        <p class="field__hint">{{ styleHint }}</p>
      </div>
    </div>

    <div class="controls__row">
      <div v-if="mode === 'exercise'" class="field field--seg">
        <span class="field__label">Accents</span>
        <div class="segment" role="radiogroup" aria-label="Accent mode">
          <button
            v-for="o in accentModes"
            :key="o.value"
            type="button"
            role="radio"
            :aria-checked="form.accents === o.value"
            :title="o.hint"
            :class="['segment__btn', { 'is-active': form.accents === o.value }]"
            @click="form.accents = o.value"
          >
            {{ o.label }}
          </button>
        </div>
        <p class="field__hint">{{ accentHint }}</p>
      </div>

      <div v-if="showHands" class="field field--seg">
        <span class="field__label">Hands</span>
        <div class="segment" role="radiogroup" aria-label="Hands">
          <button
            v-for="o in handsOpts"
            :key="o.value"
            type="button"
            role="radio"
            :aria-checked="form.hands === o.value"
            :title="o.hint"
            :class="['segment__btn', { 'is-active': form.hands === o.value }]"
            @click="form.hands = o.value"
          >
            {{ o.label }}
          </button>
        </div>
        <p class="field__hint">{{ handsHint }}</p>
      </div>
    </div>

    <button class="btn-primary controls__go" type="submit" data-tip="Generate (Enter)">
      Generate
    </button>
  </form>
</template>

<style scoped>
.controls {
  display: flex;
  flex-direction: column;
  gap: 18px;
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

.controls__row:empty {
  display: none;
}

.controls__row--top {
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

/* In a horizontal row the basis is a min WIDTH, so segments stretch to fill. */
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

.field__hint {
  margin: 2px 0 0;
  font-size: 0.72rem;
  color: var(--text-dim);
  min-height: 1em;
}

.inline {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.inline__sep {
  color: var(--text-faint);
  font-family: var(--font-mono);
}

.inline__den {
  display: inline-grid;
  place-items: center;
  min-width: 40px;
  padding: 10px 12px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: #100e0c;
  box-shadow: var(--inset);
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 1.05rem;
}

/* Segmented control: buttons stretch to fill the row; the active one is a
   subtle raised chip with amber text (not a solid fill). */
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

.segment__btn:hover:not(.is-disabled) {
  color: var(--text);
}

/* Dim via colour, NOT opacity — opacity would fade the tooltip (::after) with it. */
.segment__btn.is-disabled {
  color: #6f665a;
  cursor: not-allowed;
}

.segment__btn.is-active {
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  border-color: var(--edge);
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), 0 0 0 1px rgba(255, 157, 60, 0.18);
}

.controls__go {
  align-self: flex-end;
  min-width: 160px;
}

@media (max-width: 560px) {
  .controls__top,
  .controls__row {
    gap: 14px 16px;
  }
  .field--seg {
    flex: 1 1 100%;
  }
  /* Let 3–4 option segments wrap to two rows instead of overflowing the screen. */
  .segment {
    flex-wrap: wrap;
  }
  .segment__btn {
    flex: 1 1 42%;
    padding: 9px 10px;
    font-size: 0.85rem;
  }
}
</style>
