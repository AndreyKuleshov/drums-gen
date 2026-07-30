<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  parseFraction,
  playMetronome,
  playPhrase,
  setLoop,
  setMetroSub,
  setMetronomeVolume,
  setOverlayClick,
  setTempo,
  stopPhrase,
} from '../lib/audio'
import type { Phrase } from '../types'

const props = defineProps<{ phrase: Phrase | null; tempo: number }>()
const emit = defineEmits<{ (e: 'step', index: number | null): void }>()

const playing = ref(false)
const clicking = ref(false)
const metronome = ref(false)
const loop = ref(false)
const preroll = ref(false)
const prerollBars = ref(1)

// Metronome click subdivision (accents stay on the quarter beats).
const metroBase = ref('1/4')
const metroTriplet = ref(false)
const metroDivs = [
  { value: '1/4', label: '1/4' },
  { value: '1/8', label: '1/8' },
  { value: '1/16', label: '1/16' },
]
// Triplet subdivides a beat into 3 — only meaningful for 1/8 and 1/16. A quarter
// is the beat itself, so triplet does not apply to it.
const TRIPLET_OF: Record<string, string> = { '1/8': '1/12', '1/16': '1/24' }
const canTriplet = computed(() => metroBase.value !== '1/4')
const metroTripletOn = computed(() => metroTriplet.value && canTriplet.value)
const metroSubWhole = computed(() =>
  parseFraction(metroTripletOn.value ? TRIPLET_OF[metroBase.value] : metroBase.value),
)

// Metronome volume (0..1), applied live to standalone + overlay clicks.
const metroVolume = ref(0.75)
watch(metroVolume, (v) => setMetronomeVolume(v), { immediate: true })

// Shared subdivision: one setting drives both the overlay click and the
// standalone metronome, and applies live (no restart) to either.
watch(metroSubWhole, (v) => setMetroSub(v), { immediate: true })

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
    prerollBars: preroll.value ? prerollBars.value : 0,
    onStep: (index) => emit('step', index),
    onEnd: () => {
      playing.value = false
    },
  })
}

async function startMetronome(): Promise<void> {
  playing.value = false
  emit('step', null)
  clicking.value = true
  const num = props.phrase?.time_sig.num ?? 4
  const den = props.phrase?.time_sig.den ?? 4
  await playMetronome({ tempoBpm: props.tempo, num, den })
}

function onClickOnly(): void {
  if (clicking.value) onStop()
  else void startMetronome()
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

// The overlay click can be toggled mid-playback without restarting.
function onToggleClick(): void {
  metronome.value = !metronome.value
  if (playing.value) setOverlayClick(metronome.value)
}


function onStop(): void {
  stopPhrase()
  playing.value = false
  clicking.value = false
  emit('step', null)
}

// A new (re)generated pattern stops whatever is currently playing.
watch(
  () => props.phrase,
  () => onStop(),
)

// Spacebar toggles pattern play/stop (ignored while typing in a control).
function onKeydown(e: KeyboardEvent): void {
  if (e.code !== 'Space') return
  const tag = (e.target as HTMLElement | null)?.tagName
  if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || tag === 'BUTTON') return
  if (props.phrase === null) return
  e.preventDefault()
  if (playing.value) onStop()
  else void onPlay()
}

onMounted(() => window.addEventListener('keydown', onKeydown))

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  stopPhrase()
})
</script>

<template>
  <div class="transport">
    <div class="transport__buttons">
      <!-- Pattern transport -->
      <div class="cluster">
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
        <button class="stop" :disabled="!playing" aria-label="Stop" @click="onStop">
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
          aria-label="Loop the pattern"
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
          class="toggle"
          type="button"
          role="switch"
          :aria-checked="metronome"
          :class="{ 'is-on': metronome }"
          title="Add a metronome click over the pattern"
          @click="onToggleClick"
        >
          <span class="toggle__led" aria-hidden="true" />
          Click
        </button>

        <div class="preroll">
          <button
            class="toggle"
            type="button"
            role="switch"
            :aria-checked="preroll"
            :class="{ 'is-on': preroll }"
            title="Count-in bars of metronome before the pattern starts"
            @click="preroll = !preroll"
          >
            <span class="toggle__led" aria-hidden="true" />
            Pre-roll
          </button>
          <div v-if="preroll" class="metro-div" role="radiogroup" aria-label="Pre-roll bars">
            <button
              v-for="n in [1, 2]"
              :key="n"
              type="button"
              role="radio"
              :aria-checked="prerollBars === n"
              :class="['metro-div__btn', { 'is-active': prerollBars === n }]"
              @click="prerollBars = n"
            >
              {{ n }}
            </button>
          </div>
        </div>
      </div>

      <span class="divider" aria-hidden="true" />

      <!-- Standalone metronome (separate tool: replaces pattern playback) -->
      <div class="cluster cluster--metro">
        <button
          class="metro-btn"
          type="button"
          role="switch"
          :aria-checked="clicking"
          :class="{ 'is-on': clicking }"
          title="Practice metronome (plays on its own)"
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
          Metronome
        </button>

        <div class="metro-div" role="radiogroup" aria-label="Metronome subdivision">
          <button
            v-for="d in metroDivs"
            :key="d.value"
            type="button"
            role="radio"
            :aria-checked="metroBase === d.value"
            :class="['metro-div__btn', { 'is-active': metroBase === d.value }]"
            @click="metroBase = d.value"
          >
            {{ d.label }}
          </button>
          <button
            type="button"
            role="switch"
            :aria-checked="metroTripletOn"
            :disabled="!canTriplet"
            :class="['metro-div__btn', 'metro-div__trip', { 'is-active': metroTripletOn }]"
            title="Triplet subdivision (eighth/sixteenth only)"
            @click="metroTriplet = !metroTriplet"
          >
            T
          </button>
        </div>

        <label class="volume" title="Metronome volume">
          <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
            <path
              d="M4 9v6h4l5 4V5L8 9zM16 8.5a4 4 0 0 1 0 7M18.5 6a7 7 0 0 1 0 12"
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          <input
            v-model.number="metroVolume"
            class="volume__range"
            type="range"
            min="0"
            max="1"
            step="0.01"
            aria-label="Metronome volume"
          />
        </label>
      </div>
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
  gap: 16px;
  flex-wrap: wrap;
}

.cluster {
  display: flex;
  align-items: center;
  gap: 12px;
}

.divider {
  width: 1px;
  align-self: stretch;
  min-height: 40px;
  background: var(--hairline);
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

/* "Click" overlay toggle (part of the pattern transport) */
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
  font-size: 0.7rem;
  letter-spacing: 0.12em;
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

.preroll {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

/* Standalone metronome (its own tool) */
.metro-btn {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 10px 16px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  box-shadow: var(--shadow-1);
  transition:
    color 0.15s ease,
    box-shadow 0.18s ease,
    transform 0.12s ease;
}

.metro-btn:hover {
  color: var(--text);
}

.metro-btn:active {
  transform: translateY(1px);
}

.metro-btn.is-on {
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), 0 0 16px -5px var(--amber-glow), inset 0 0 0 1px rgba(255, 157, 60, 0.3);
  /* Gentle pulse so a running standalone metronome has a visual presence. */
  animation: metro-pulse 1.4s ease-in-out infinite;
}

@keyframes metro-pulse {
  0%,
  100% {
    box-shadow: var(--shadow-1), 0 0 14px -6px var(--amber-glow), inset 0 0 0 1px rgba(255, 157, 60, 0.3);
  }
  50% {
    box-shadow: var(--shadow-1), 0 0 22px -2px var(--amber-glow), inset 0 0 0 1px rgba(255, 157, 60, 0.5);
  }
}

.metro-div {
  display: inline-flex;
  padding: 3px;
  gap: 3px;
  background: #100e0c;
  border: 1px solid var(--edge);
  border-radius: var(--r-md);
  box-shadow: var(--inset);
}

.metro-div__btn {
  min-width: 34px;
  padding: 6px 8px;
  border: 1px solid transparent;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.74rem;
  transition:
    background 0.16s ease,
    color 0.16s ease;
}

.metro-div__btn:hover:not(:disabled) {
  color: var(--text);
}

.metro-div__btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.metro-div__trip {
  min-width: 28px;
}

.metro-div__btn.is-active {
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  border-color: var(--edge);
  color: var(--amber-bright);
  box-shadow: var(--shadow-1);
}

.volume {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-faint);
}

.volume__range {
  width: 84px;
  height: 4px;
  border-radius: 4px;
  background: #100e0c;
  box-shadow: var(--inset);
  appearance: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.volume__range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: linear-gradient(180deg, var(--amber-bright), var(--amber));
  border: 1px solid var(--amber-dim);
  box-shadow: 0 0 8px -2px var(--amber-glow);
}

.volume__range::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border: 1px solid var(--amber-dim);
  border-radius: 50%;
  background: var(--amber);
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
  /* Stack the transport into full-width rows so nothing clips off the chassis. */
  .transport__buttons {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
    gap: 14px;
  }
  .cluster {
    justify-content: center;
    flex-wrap: wrap;
  }
  .cluster--metro {
    flex-wrap: wrap;
    gap: 10px;
  }
  .divider {
    width: 100%;
    min-height: 1px;
    height: 1px;
  }
  .volume {
    flex: 1 1 140px;
  }
  .volume__range {
    flex: 1 1 auto;
    width: auto;
    min-width: 0;
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
