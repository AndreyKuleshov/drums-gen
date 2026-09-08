<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import GrooveScore from '../components/GrooveScore.vue'
import ScoreView from '../components/ScoreView.vue'
import Stepper from '../components/Stepper.vue'
import TransportRack from '../components/TransportRack.vue'
import type { PlayEngine } from '../components/TransportRack.vue'
import { ApiError, apiFetch } from '../lib/api'
import { playPhrase, stopPhrase } from '../lib/audio'
import { playGroove, stopGroove } from '../lib/kit'
import { persistedRef } from '../lib/storage'
import type { Groove, Phrase } from '../types'

const tempo = persistedRef('patterns2-tempo', 100)
const bars = persistedRef('patterns2-bars', 2)
const subdivision = persistedRef('patterns2-sub', '1/16')
const singles = persistedRef('patterns2-singles', true)
const odd = persistedRef('patterns2-odd', true)
const paradiddle = persistedRef('patterns2-paradiddle', true)
// 'snare' = pure sticking on the snare; 'kit' = orchestrated across the kit.
const voicing = persistedRef<'snare' | 'kit'>('patterns2-voicing', 'snare')
const voicings: { v: 'snare' | 'kit'; label: string }[] = [
  { v: 'snare', label: 'Snare' },
  { v: 'kit', label: 'Kit' },
]

const phrase = ref<Phrase | null>(null)
const groove = ref<Groove | null>(null)
const activeStep = ref<number | null>(null)
const error = ref('')

const transport = ref<InstanceType<typeof TransportRack> | null>(null)
const canPlay = computed(() => phrase.value !== null || groove.value !== null)
const meter = { num: 4, den: 4 }

const phraseEngine: PlayEngine = {
  play: async (o) => {
    if (phrase.value !== null) await playPhrase(phrase.value, o)
  },
  stop: stopPhrase,
}
const grooveEngine: PlayEngine = {
  play: async (o) => {
    if (groove.value !== null) await playGroove(groove.value, o)
  },
  stop: stopGroove,
}
const engine = computed<PlayEngine>(() => (groove.value !== null ? grooveEngine : phraseEngine))

async function generate(): Promise<void> {
  // Regenerating stops any playing pattern (same as the Studio tab), so the old
  // pattern doesn't keep sounding under the new one.
  transport.value?.stop()
  activeStep.value = null
  error.value = ''
  if (!singles.value && !odd.value && !paradiddle.value) {
    error.value = 'Enable at least one block family.'
    return
  }
  const body = JSON.stringify({
    time_sig: meter,
    num_bars: bars.value,
    subdivision: subdivision.value,
    tempo_bpm: tempo.value,
    singles: singles.value,
    odd: odd.value,
    paradiddle: paradiddle.value,
    voicing: voicing.value,
  })
  try {
    // The endpoint returns a monophonic Phrase for 'snare' or a polyphonic
    // Groove for 'kit'; fetch the shape we asked for and clear the other.
    if (voicing.value === 'kit') {
      groove.value = await apiFetch<Groove>('/patterns2/generate', { method: 'POST', body })
      phrase.value = null
    } else {
      phrase.value = await apiFetch<Phrase>('/patterns2/generate', { method: 'POST', body })
      groove.value = null
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
          <GrooveScore v-if="groove" :groove="groove" :active-step="activeStep" />
          <ScoreView v-else-if="phrase" :phrase="phrase" :active-step="activeStep" />
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

          <div class="field field--seg field--narrow">
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

          <div class="field field--seg field--narrow">
            <span class="field__label">Subdivision</span>
            <div class="segment" role="radiogroup" aria-label="Subdivision">
              <button
                v-for="s in ['1/8', '1/16']"
                :key="s"
                type="button"
                role="radio"
                :aria-checked="subdivision === s"
                :class="['segment__btn', { 'is-active': subdivision === s }]"
                @click="subdivision = s"
              >
                {{ s }}
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

.field--narrow {
  flex: 0 1 168px;
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

.screen {
  border-radius: var(--r-lg);
  padding: 10px;
  background: linear-gradient(180deg, #0f0d0b, #171310);
  border: 1px solid var(--edge);
}
.screen__glass {
  min-height: 200px;
  border-radius: var(--r-md);
  background: linear-gradient(180deg, #fbf6ec, var(--screen));
  border: 1px solid var(--screen-edge);
  display: flex;
  align-items: center;
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
  .field--seg,
  .field--narrow {
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
</style>
