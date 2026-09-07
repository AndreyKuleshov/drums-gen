<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import ScoreView from '../components/ScoreView.vue'
import TransportRack from '../components/TransportRack.vue'
import type { PlayEngine } from '../components/TransportRack.vue'
import { apiFetch } from '../lib/api'
import { playPhrase, stopPhrase } from '../lib/audio'
import { persistedRef } from '../lib/storage'
import type { Phrase } from '../types'

const tempo = persistedRef('patterns2-tempo', 100)
const bars = persistedRef('patterns2-bars', 2)
const subdivision = persistedRef('patterns2-sub', '1/16')
const singles = persistedRef('patterns2-singles', true)
const odd = persistedRef('patterns2-odd', true)
const paradiddle = persistedRef('patterns2-paradiddle', true)

const phrase = ref<Phrase | null>(null)
const activeStep = ref<number | null>(null)
const error = ref('')

const transport = ref<InstanceType<typeof TransportRack> | null>(null)
const canPlay = computed(() => phrase.value !== null)
const meter = { num: 4, den: 4 }

const engine: PlayEngine = {
  play: async (o) => {
    if (phrase.value !== null) await playPhrase(phrase.value, o)
  },
  stop: stopPhrase,
}

async function generate(): Promise<void> {
  error.value = ''
  if (!singles.value && !odd.value && !paradiddle.value) {
    error.value = 'Enable at least one block family.'
    return
  }
  try {
    phrase.value = await apiFetch<Phrase>('/patterns2/generate', {
      method: 'POST',
      body: JSON.stringify({
        time_sig: meter,
        num_bars: bars.value,
        subdivision: subdivision.value,
        tempo_bpm: tempo.value,
        singles: singles.value,
        odd: odd.value,
        paradiddle: paradiddle.value,
      }),
    })
  } catch {
    error.value = 'Couldn’t generate. Is the engine running?'
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
          <ScoreView v-if="phrase" :phrase="phrase" :active-step="activeStep" />
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

      <p v-if="error" class="formmsg--error" role="alert">{{ error }}</p>

      <section class="controls">
        <div class="families" role="group" aria-label="Block families">
          <button type="button" :class="{ on: singles }" @click="singles = !singles">Singles</button>
          <button type="button" :class="{ on: odd }" @click="odd = !odd">Odd 3/5/7</button>
          <button type="button" :class="{ on: paradiddle }" @click="paradiddle = !paradiddle">
            Paradiddle
          </button>
        </div>

        <div class="field">
          <span class="field__label">Subdivision</span>
          <button
            v-for="s in ['1/8', '1/16']"
            :key="s"
            type="button"
            :class="{ on: subdivision === s }"
            @click="subdivision = s"
          >
            {{ s }}
          </button>
        </div>

        <label class="field">
          <span class="field__label">Bars</span>
          <input v-model.number="bars" type="number" min="1" max="16" />
        </label>

        <label class="field">
          <span class="field__label">Tempo</span>
          <input v-model.number="tempo" type="number" min="30" max="300" />
        </label>

        <button class="generate" type="button" data-test="generate" @click="generate">
          Generate
        </button>
      </section>
    </div>
  </main>
</template>

<style scoped>
.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.families,
.field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.field__label {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-dim);
}
.controls button {
  padding: 8px 12px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  cursor: pointer;
}
.controls button.on {
  color: var(--amber-bright);
  box-shadow: inset 0 0 0 1px rgba(255, 157, 60, 0.3);
}
.generate {
  margin-left: auto;
  color: var(--amber-bright) !important;
}
.controls input {
  width: 64px;
  padding: 7px 8px;
  border-radius: var(--r-sm);
  border: 1px solid var(--edge);
  background: #100e0c;
  color: var(--text);
  font-family: var(--font-mono);
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
</style>
