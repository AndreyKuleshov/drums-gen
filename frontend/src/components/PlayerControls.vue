<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { playMetronome, playPhrase, setLoop, setTempo, stopPhrase } from '../lib/audio'
import type { Phrase } from '../types'

const props = defineProps<{ phrase: Phrase | null; tempo: number }>()
const emit = defineEmits<{ (e: 'step', index: number | null): void }>()

const playing = ref(false)
const clicking = ref(false)
const metronome = ref(false)
const loop = ref(false)

const meta = computed(() => {
  if (props.phrase === null) return null
  const strokes = props.phrase.bars.flatMap((b) => b.strokes)
  return { bars: props.phrase.bars.length, notes: strokes.length }
})

async function onPlay(): Promise<void> {
  if (props.phrase === null) return
  clicking.value = false
  playing.value = true
  await playPhrase(props.phrase, {
    metronome: metronome.value,
    loop: loop.value,
    tempoBpm: props.tempo,
    onStep: (index) => emit('step', index),
    onEnd: () => {
      playing.value = false
    },
  })
}

async function onClickOnly(): Promise<void> {
  if (clicking.value) {
    onStop()
    return
  }
  playing.value = false
  emit('step', null)
  clicking.value = true
  const num = props.phrase?.time_sig.num ?? 4
  const den = props.phrase?.time_sig.den ?? 4
  await playMetronome({ tempoBpm: props.tempo, num, den })
}

// Tempo is live: changing it retimes the running transport without restarting.
watch(
  () => props.tempo,
  (bpm) => {
    if (playing.value || clicking.value) setTempo(bpm)
  },
)

// Loop can be toggled mid-playback and takes effect immediately.
function onToggleLoop(): void {
  loop.value = !loop.value
  if (playing.value) setLoop(loop.value)
}

function onStop(): void {
  stopPhrase()
  playing.value = false
  clicking.value = false
  emit('step', null)
}

onBeforeUnmount(() => {
  stopPhrase()
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
      <button class="stop" :disabled="!playing && !clicking" aria-label="Stop" @click="onStop">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor" />
        </svg>
      </button>

      <button
        class="icon-btn"
        type="button"
        role="switch"
        :class="{ 'is-on': loop }"
        :aria-checked="loop"
        aria-label="Loop"
        title="Loop the pattern"
        @click="onToggleLoop"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            d="M7 7h9a4 4 0 0 1 4 4M17 17H8a4 4 0 0 1-4-4"
            fill="none"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path d="M15 4.5 18 7l-3 2.5M9 19.5 6 17l3-2.5" fill="currentColor" />
        </svg>
      </button>

      <button
        class="icon-btn"
        type="button"
        :class="{ 'is-on': clicking }"
        :aria-pressed="clicking"
        aria-label="Metronome only"
        title="Play metronome only"
        @click="onClickOnly"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            d="M9 3h6l3 16H6zM12 6.5v8.5M12 15l4-3"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
        </svg>
      </button>

      <button
        class="metro"
        type="button"
        role="switch"
        :aria-checked="metronome"
        :class="{ 'is-on': metronome }"
        @click="metronome = !metronome"
      >
        <span class="metro__led" aria-hidden="true" />
        With click
      </button>

      <span class="status">
        <span
          class="status__led"
          :class="{ 'status__led--on': playing || clicking }"
          aria-hidden="true"
        />
        {{ clicking ? 'Click' : playing ? 'Playing' : phrase ? 'Ready' : 'No pattern' }}
      </span>
    </div>

    <dl v-if="meta" class="readout">
      <div><dt>Tempo</dt><dd>{{ tempo }}<small> BPM</small></dd></div>
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

.icon-btn {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid var(--edge);
  color: var(--text-dim);
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  box-shadow: var(--shadow-1);
  transition:
    color 0.15s ease,
    box-shadow 0.2s ease,
    transform 0.12s cubic-bezier(0.2, 0.7, 0.3, 1);
}

.icon-btn:hover {
  color: var(--text);
}

.icon-btn:active {
  transform: translateY(1px);
}

.icon-btn.is-on {
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), 0 0 16px -4px var(--amber-glow), inset 0 0 0 1px rgba(255, 157, 60, 0.3);
}

.play:disabled,
.stop:disabled {
  filter: saturate(0.4) brightness(0.7);
}

.metro {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  box-shadow: var(--shadow-1);
  transition:
    color 0.15s ease,
    box-shadow 0.18s ease;
}

.metro:hover {
  color: var(--text);
}

.metro.is-on {
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), inset 0 0 0 1px rgba(255, 157, 60, 0.25);
}

.metro__led {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: var(--edge);
}

.metro.is-on .metro__led {
  background: var(--amber);
  box-shadow: 0 0 9px 1px var(--amber-glow);
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
