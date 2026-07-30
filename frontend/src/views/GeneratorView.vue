<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import GenerationForm from '../components/GenerationForm.vue'
import PlayerControls from '../components/PlayerControls.vue'
import ScoreView from '../components/ScoreView.vue'
import { persistedRef } from '../lib/storage'
import type { PatternConfig, Phrase } from '../types'

const phrase = ref<Phrase | null>(null)
const activeStep = ref<number | null>(null)
const tempo = persistedRef('tempo', 100)
const config = ref<PatternConfig | null>(null)
const booting = ref(false)
let bootTimer: ReturnType<typeof setTimeout> | null = null

const cap = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)

// The plate always reflects the live form config; Notes appears once generated.
const summary = computed(() => {
  const c = config.value
  if (c === null) return null
  return {
    level: cap(c.difficulty),
    meter: c.meter,
    grid: c.grid,
    feel: cap(c.feel),
    accents: cap(c.accents),
    bars: c.bars,
    notes:
      phrase.value === null
        ? null
        : phrase.value.bars.reduce((n, b) => n + b.strokes.length, 0),
  }
})

function onGenerated(next: Phrase): void {
  activeStep.value = null
  phrase.value = next
  booting.value = false
  if (bootTimer !== null) clearTimeout(bootTimer)
  requestAnimationFrame(() => {
    booting.value = true
    bootTimer = setTimeout(() => (booting.value = false), 600)
  })
}
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">Drum Pattern Generator</span>
        </div>
        <div class="brand__meta">
          <span class="brand__model">RG&#8209;40 · RUDIMENT ENGINE</span>
          <RouterLink to="/rudiments" class="nav-link">Rudiments &rarr;</RouterLink>
          <span class="led led--on" aria-hidden="true" />
        </div>
      </header>

      <section class="screen" aria-label="Notation display">
        <div class="screen__glass" :class="{ 'screen__glass--boot': booting }">
          <ScoreView v-if="phrase" :phrase="phrase" :active-step="activeStep" />
          <div v-else class="screen__empty">
            <span class="screen__empty-glyph" aria-hidden="true">&#9833;</span>
            <p class="screen__empty-text">
              Set the meter and hit <strong>Generate</strong> to score a rudiment phrase.
            </p>
          </div>
        </div>

        <dl v-if="summary" class="specplate" aria-label="Pattern summary">
          <div><dt>Level</dt><dd>{{ summary.level }}</dd></div>
          <div><dt>Meter</dt><dd>{{ summary.meter }}</dd></div>
          <div><dt>Grid</dt><dd>{{ summary.grid }}</dd></div>
          <div><dt>Feel</dt><dd>{{ summary.feel }}</dd></div>
          <div><dt>Accents</dt><dd>{{ summary.accents }}</dd></div>
          <div><dt>Bars</dt><dd>{{ summary.bars }}</dd></div>
          <div><dt>Notes</dt><dd>{{ summary.notes ?? '—' }}</dd></div>
          <div><dt>Tempo</dt><dd>{{ tempo }}<small>bpm</small></dd></div>
        </dl>
      </section>

      <PlayerControls :phrase="phrase" :tempo="tempo" @step="activeStep = $event" />

      <GenerationForm
        v-model:tempo="tempo"
        @update:phrase="onGenerated"
        @update:config="config = $event"
      />
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

.screen__empty-text strong {
  color: var(--amber-dim);
  font-weight: 600;
}
</style>
