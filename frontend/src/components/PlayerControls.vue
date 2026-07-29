<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

import { parseFraction, playPhrase, stopPhrase } from '../lib/audio'
import type { Phrase } from '../types'

const props = defineProps<{ phrase: Phrase | null }>()

const playing = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

const meta = computed(() => {
  if (props.phrase === null) return null
  const strokes = props.phrase.bars.flatMap((b) => b.strokes)
  return { tempo: props.phrase.tempo_bpm, bars: props.phrase.bars.length, notes: strokes.length }
})

function durationSec(phrase: Phrase): number {
  const wholeNotes = phrase.bars
    .flatMap((b) => b.strokes)
    .reduce((sum, s) => sum + parseFraction(s.duration), 0)
  return wholeNotes * (240 / phrase.tempo_bpm)
}

async function onPlay(): Promise<void> {
  if (props.phrase === null) return
  if (timer !== null) clearTimeout(timer)
  await playPhrase(props.phrase)
  playing.value = true
  timer = setTimeout(() => (playing.value = false), durationSec(props.phrase) * 1000 + 250)
}

function onStop(): void {
  stopPhrase()
  playing.value = false
  if (timer !== null) clearTimeout(timer)
}

onBeforeUnmount(() => {
  if (timer !== null) clearTimeout(timer)
})
</script>

<template>
  <div class="transport">
    <div class="transport__buttons">
      <button
        class="play"
        :class="{ 'is-playing': playing }"
        :disabled="phrase === null"
        :aria-label="playing ? 'Playing' : 'Play'"
        @click="onPlay"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path d="M8 5.5v13l11-6.5z" fill="currentColor" />
        </svg>
      </button>
      <button class="stop" :disabled="phrase === null" aria-label="Stop" @click="onStop">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor" />
        </svg>
      </button>
      <span class="status">
        <span class="status__led" :class="{ 'status__led--on': playing }" aria-hidden="true" />
        {{ playing ? 'Playing' : phrase ? 'Ready' : 'No pattern' }}
      </span>
    </div>

    <dl v-if="meta" class="readout">
      <div><dt>Tempo</dt><dd>{{ meta.tempo }}<small> BPM</small></dd></div>
      <div><dt>Bars</dt><dd>{{ meta.bars }}</dd></div>
      <div><dt>Notes</dt><dd>{{ meta.notes }}</dd></div>
    </dl>
  </div>
</template>

<style scoped>
.transport {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px 16px;
  background: linear-gradient(180deg, var(--raised), var(--panel));
  border: 1px solid var(--edge);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-2), inset 0 1px 0 rgba(239, 231, 216, 0.05);
}

.transport__buttons {
  display: flex;
  align-items: center;
  gap: 14px;
}

.play,
.stop {
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid var(--edge);
  transition:
    transform 0.12s cubic-bezier(0.2, 0.7, 0.3, 1),
    box-shadow 0.2s ease,
    filter 0.18s ease;
}

.play {
  width: 56px;
  height: 56px;
  padding-left: 2px;
  color: #221204;
  background: linear-gradient(180deg, var(--amber-bright), var(--amber));
  border-color: var(--amber-dim);
  box-shadow: var(--shadow-2), 0 0 22px -6px var(--amber-glow);
}

.play:hover:not(:disabled) {
  filter: brightness(1.06);
}

.play:active:not(:disabled) {
  transform: translateY(1px);
}

.play.is-playing {
  box-shadow: var(--shadow-2), 0 0 28px -2px var(--amber-glow);
  animation: pulse 1.4s ease-in-out infinite;
}

.stop {
  width: 44px;
  height: 44px;
  color: var(--text-dim);
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  box-shadow: var(--shadow-1);
}

.stop:hover:not(:disabled) {
  color: var(--text);
}

.stop:active:not(:disabled) {
  transform: translateY(1px);
}

.play:disabled,
.stop:disabled {
  filter: saturate(0.4) brightness(0.7);
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-dim);
}

.status__led {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--edge);
}

.status__led--on {
  background: var(--amber);
  box-shadow: 0 0 10px 1px var(--amber-glow);
}

.readout {
  display: flex;
  gap: 22px;
  margin: 0;
}

.readout div {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.readout dt {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.readout dd {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 1.02rem;
  font-weight: 500;
  color: var(--amber-bright);
}

.readout dd small {
  font-size: 0.62rem;
  color: var(--text-faint);
  letter-spacing: 0.08em;
}

@keyframes pulse {
  0%,
  100% {
    box-shadow: var(--shadow-2), 0 0 20px -6px var(--amber-glow);
  }
  50% {
    box-shadow: var(--shadow-2), 0 0 34px 0 var(--amber-glow);
  }
}

@media (max-width: 560px) {
  .transport {
    justify-content: center;
  }
  .readout {
    width: 100%;
    justify-content: space-around;
  }
  .readout div {
    align-items: center;
  }
}
</style>
