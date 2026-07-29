<script setup lang="ts">
import { reactive, ref } from 'vue'

import { apiUrl } from '../lib/api'
import type { Phrase } from '../types'
import Stepper from './Stepper.vue'

const emit = defineEmits<{ (e: 'update:phrase', phrase: Phrase): void }>()

const form = reactive({
  num: 4,
  den: 4,
  num_bars: 2,
  base: '1/16',
  triplet: false,
  tempo_bpm: 100,
  accent_mode: 'rudiment',
})

const bases = [
  { value: '1/8', label: '1/8' },
  { value: '1/16', label: '1/16' },
]
const accentModes = [
  { value: 'rudiment', label: 'Rudiment' },
  { value: 'metric', label: 'Metric' },
  { value: 'both', label: 'Both' },
]

// Triplet turns a straight subdivision into its triplet grid (1/8 -> 1/12, 1/16 -> 1/24).
const TRIPLET_OF: Record<string, string> = { '1/8': '1/12', '1/16': '1/24' }

const error = ref('')
const loading = ref(false)

async function submit(): Promise<void> {
  error.value = ''
  loading.value = true
  const subdivision = form.triplet ? (TRIPLET_OF[form.base] ?? form.base) : form.base
  try {
    const resp = await fetch(apiUrl('/generate'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        time_sig: { num: form.num, den: form.den },
        num_bars: form.num_bars,
        min_subdivision: subdivision,
        tempo_bpm: form.tempo_bpm,
        accent_mode: form.accent_mode,
      }),
    })
    if (!resp.ok) {
      error.value =
        resp.status === 422
          ? 'Those settings can’t be scored — try a simpler meter or subdivision.'
          : `Generation failed (${resp.status}).`
      return
    }
    emit('update:phrase', (await resp.json()) as Phrase)
  } catch {
    error.value = 'Can’t reach the engine. Is the backend running?'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="panel" @submit.prevent="submit">
    <div class="controls">
      <div class="field field--sig">
        <span class="field__label">Meter</span>
        <div class="sig">
          <Stepper v-model="form.num" :min="1" :max="16" label="Beats per bar" />
          <span class="sig__slash">/</span>
          <Stepper v-model="form.den" :min="1" :max="16" label="Beat unit" />
        </div>
      </div>

      <div class="field">
        <span class="field__label">Bars</span>
        <Stepper v-model="form.num_bars" :min="1" :max="64" label="Number of bars" />
      </div>

      <div class="field field--seg">
        <span class="field__label">Subdivision</span>
        <div class="subdiv">
          <div class="segment" role="radiogroup" aria-label="Subdivision">
            <button
              v-for="opt in bases"
              :key="opt.value"
              type="button"
              role="radio"
              :aria-checked="form.base === opt.value"
              :class="['segment__btn', { 'is-active': form.base === opt.value }]"
              @click="form.base = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>
          <button
            type="button"
            role="switch"
            :aria-checked="form.triplet"
            :class="['toggle', { 'is-on': form.triplet }]"
            @click="form.triplet = !form.triplet"
          >
            <span class="toggle__led" aria-hidden="true" />
            Triplet
          </button>
        </div>
      </div>

      <div class="field">
        <span class="field__label">Tempo</span>
        <div class="tempo">
          <Stepper v-model="form.tempo_bpm" :min="20" :max="300" :step="2" label="Tempo" />
          <span class="tempo__unit">BPM</span>
        </div>
      </div>

      <div class="field field--seg field--wide">
        <span class="field__label">Accents</span>
        <div class="segment" role="radiogroup" aria-label="Accent mode">
          <button
            v-for="opt in accentModes"
            :key="opt.value"
            type="button"
            role="radio"
            :aria-checked="form.accent_mode === opt.value"
            :class="['segment__btn', { 'is-active': form.accent_mode === opt.value }]"
            @click="form.accent_mode = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
    </div>

    <div class="actions">
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="generate" type="submit" :disabled="loading">
        <span v-if="loading" class="generate__spin" aria-hidden="true" />
        {{ loading ? 'Scoring…' : 'Generate' }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.panel {
  background: linear-gradient(180deg, var(--raised), var(--panel));
  border: 1px solid var(--edge);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-2), inset 0 1px 0 rgba(239, 231, 216, 0.05);
  padding: clamp(14px, 2vw, 20px);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
}

.field--sig,
.field:not(.field--seg) {
  flex: 0 0 auto;
}

.field--seg {
  flex: 1 1 200px;
}

.field--wide {
  flex-basis: 260px;
}

.field__label {
  font-family: var(--font-mono);
  font-size: 0.66rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.sig {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sig__slash {
  font-family: var(--font-mono);
  font-size: 1.2rem;
  color: var(--text-faint);
}

.tempo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tempo__unit {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  color: var(--text-faint);
}

.subdiv {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  box-shadow: var(--shadow-1);
  transition:
    color 0.15s ease,
    box-shadow 0.18s ease;
}

.toggle:hover {
  color: var(--text);
}

.toggle.is-on {
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), inset 0 0 0 1px rgba(255, 157, 60, 0.25);
}

.toggle__led {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--edge);
}

.toggle.is-on .toggle__led {
  background: var(--amber);
  box-shadow: 0 0 9px 1px var(--amber-glow);
}

.segment {
  display: inline-flex;
  padding: 4px;
  gap: 4px;
  background: #100e0c;
  border: 1px solid var(--edge);
  border-radius: var(--r-md);
  box-shadow: var(--inset);
}

.segment__btn {
  flex: 1 1 auto;
  padding: 8px 14px;
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text-dim);
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
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

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}

.error {
  flex: 1 1 auto;
  color: var(--danger);
  font-size: 0.88rem;
}

.generate {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 13px 30px;
  border: 1px solid var(--amber-dim);
  border-radius: var(--r-md);
  background: linear-gradient(180deg, var(--amber-bright), var(--amber));
  color: #221204;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1rem;
  letter-spacing: -0.01em;
  box-shadow: var(--shadow-2), 0 0 24px -6px var(--amber-glow);
  transition:
    transform 0.12s cubic-bezier(0.2, 0.7, 0.3, 1),
    box-shadow 0.18s ease,
    filter 0.18s ease;
}

.generate:hover:not(:disabled) {
  filter: brightness(1.06);
  box-shadow: var(--shadow-2), 0 0 32px -4px var(--amber-glow);
}

.generate:active:not(:disabled) {
  transform: translateY(1px);
}

.generate:disabled {
  filter: saturate(0.5) brightness(0.8);
}

.generate__spin {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(34, 18, 4, 0.4);
  border-top-color: #221204;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 560px) {
  .field,
  .field--seg,
  .field--wide {
    flex: 1 1 100%;
  }
  .segment {
    width: 100%;
  }
  .generate {
    width: 100%;
    justify-content: center;
  }
}
</style>
