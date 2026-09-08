<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { persistedRef } from '../lib/storage'
import {
  parseFraction,
  playMetronome,
  setLoop,
  setMetroSub,
  setMetronomeVolume,
  setOverlayClick,
  setTempo,
  stopPhrase,
} from '../lib/audio'

/** Playback options common to both engines (rudiment phrase + full-kit groove). */
export interface PlayOpts {
  metronome: boolean
  loop: boolean
  tempoBpm: number
  prerollBars: number
  onStep: (index: number | null) => void
  onEnd: () => void
}
export interface PlayEngine {
  play: (opts: PlayOpts) => Promise<void>
  stop: () => void
}

const props = defineProps<{
  /** Whether there is content to play (a generated phrase/groove). */
  canPlay: boolean
  /** Current meter, for the standalone metronome bar length. */
  meter: { num: number; den: number }
  /** Live playback tempo (BPM). */
  tempo: number
  /** The mode's playback engine — play(opts) / stop(). */
  engine: PlayEngine
}>()
const emit = defineEmits<{ (e: 'step', index: number | null): void }>()

const playing = ref(false)
// True while the first Play is fetching/decoding the kit samples — playback can't
// start until they're loaded, so we show a spinner instead of a dead button.
const preparing = ref(false)
const clicking = ref(false)
// Metronome + transport prefs are shared across modes (one source of truth).
const metronome = persistedRef('metronome', false)
const loop = persistedRef('loop', false)
const preroll = persistedRef('preroll', false)
const prerollBars = persistedRef('prerollBars', 1)

const metroBase = persistedRef('metroBase', '1/4')
const metroTriplet = persistedRef('metroTriplet', false)
const metroDivs = [
  { value: '1/4', label: '1/4' },
  { value: '1/8', label: '1/8' },
  { value: '1/16', label: '1/16' },
]
const TRIPLET_OF: Record<string, string> = { '1/8': '1/12', '1/16': '1/24' }
const canTriplet = computed(() => metroBase.value !== '1/4')
const metroTripletOn = computed(() => metroTriplet.value && canTriplet.value)
const metroSubWhole = computed(() =>
  parseFraction(metroTripletOn.value ? TRIPLET_OF[metroBase.value] : metroBase.value),
)

const metroVolume = persistedRef('metroVolume', 0.75)
watch(metroVolume, (v) => setMetronomeVolume(v), { immediate: true })
watch(metroSubWhole, (v) => setMetroSub(v), { immediate: true })

async function onPlay(): Promise<void> {
  if (!props.canPlay || preparing.value) return
  clicking.value = false
  preparing.value = true
  try {
    // Resolves only once the samples are loaded and the transport has started,
    // so `preparing` spans exactly the (first-play) loading window.
    await props.engine.play({
      metronome: metronome.value,
      loop: loop.value,
      tempoBpm: props.tempo,
      prerollBars: preroll.value ? prerollBars.value : 0,
      onStep: (index) => emit('step', index),
      onEnd: () => {
        playing.value = false
      },
    })
    playing.value = true
  } finally {
    preparing.value = false
  }
}

async function startMetronome(): Promise<void> {
  playing.value = false
  emit('step', null)
  clicking.value = true
  await playMetronome({ tempoBpm: props.tempo, num: props.meter.num, den: props.meter.den })
}

function onClickOnly(): void {
  if (playing.value) return
  if (clicking.value) onStop()
  else void startMetronome()
}

watch(
  () => props.tempo,
  (bpm) => {
    if (playing.value || clicking.value) setTempo(bpm)
  },
)

function onToggleLoop(): void {
  loop.value = !loop.value
  if (playing.value) setLoop(loop.value)
}

function onToggleClick(): void {
  metronome.value = !metronome.value
  if (playing.value) setOverlayClick(metronome.value)
}

function onStop(): void {
  props.engine.stop()
  playing.value = false
  clicking.value = false
  emit('step', null)
}

function onToggle(): void {
  if (playing.value) onStop()
  else void onPlay()
}

// The parent (StudioView) owns the keyboard shortcuts and drives these.
defineExpose({ toggle: onToggle, stop: onStop, toggleLoop: onToggleLoop, toggleClick: onToggleClick })

onBeforeUnmount(() => stopPhrase())
</script>

<template>
  <div class="rack">
    <div class="transport">
      <div class="cluster">
        <button
          class="play"
          :class="{ 'is-playing': playing, 'is-loading': preparing }"
          :disabled="!canPlay || preparing"
          :aria-label="preparing ? 'Loading sounds' : playing ? 'Playing' : 'Play'"
          :aria-busy="preparing || undefined"
          :data-tip="preparing ? 'Loading sounds…' : 'Play / Stop (Space)'"
          data-tip-pos="below" data-tip-align="left"
          @click="onPlay"
        >
          <svg
            v-if="preparing"
            class="play__spinner"
            viewBox="0 0 24 24"
            width="20"
            height="20"
            aria-hidden="true"
          >
            <circle
              cx="12"
              cy="12"
              r="8"
              fill="none"
              stroke="currentColor"
              stroke-width="2.4"
              stroke-linecap="round"
              stroke-dasharray="38 60"
            />
          </svg>
          <svg v-else viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
            <path d="M8 5.5v13l11-6.5z" fill="currentColor" />
          </svg>
        </button>
        <button class="stop" :disabled="!playing" aria-label="Stop" data-tip="Stop (Space)" data-tip-pos="below" @click="onStop">
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
          data-tip="Loop (R)" data-tip-pos="below"
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
          data-tip="Click (C)" data-tip-pos="below"
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
            data-tip="Count-in before playback" data-tip-pos="below"
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
    </div>

    <section class="metro-panel" aria-label="Metronome">
      <span class="metro-panel__title">
        Metronome
        <span class="metro-panel__hint">plays on its own · also sets the pattern click</span>
      </span>

      <div class="metro-panel__controls">
        <button
          class="metro-btn"
          type="button"
          role="switch"
          :aria-checked="clicking"
          :aria-label="clicking ? 'Stop metronome' : 'Start metronome'"
          :disabled="playing"
          :class="{ 'is-on': clicking }"
          data-tip="Practice metronome"
          @click="onClickOnly"
        >
          <svg v-if="!clicking" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path d="M8 5.5v13l11-6.5z" fill="currentColor" />
          </svg>
          <svg v-else viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
            <rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor" />
          </svg>
          {{ clicking ? 'Stop' : 'Start' }}
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
            data-tip="Triplet subdivision"
            @click="metroTriplet = !metroTriplet"
          >
            T
          </button>
        </div>

        <label class="volume" data-tip="Metronome volume">
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
    </section>
  </div>
</template>

<style scoped>
.rack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

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

.metro-panel {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 10px 16px;
  background: linear-gradient(180deg, #171310, var(--chassis));
  border: 1px solid var(--edge-soft);
  border-radius: var(--r-lg);
  box-shadow: var(--inset);
}

.metro-panel__title {
  display: flex;
  flex-direction: column;
  gap: 1px;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-dim);
}

.metro-panel__hint {
  font-size: 0.56rem;
  letter-spacing: 0.06em;
  text-transform: none;
  color: var(--text-faint);
}

.metro-panel__controls {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-left: auto;
}

.cluster {
  display: flex;
  align-items: center;
  gap: 12px;
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
  color: var(--amber-bright);
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  border: 1.5px solid var(--amber-dim);
  box-shadow: var(--shadow-1), inset 0 0 0 1px rgba(255, 157, 60, 0.18);
}

.play:hover:not(:disabled) {
  filter: brightness(1.1);
  box-shadow: var(--shadow-1), 0 0 18px -6px var(--amber-glow);
}

.play:active:not(:disabled) {
  transform: translateY(1px);
}

.play.is-playing {
  color: #221204;
  background: linear-gradient(180deg, var(--amber-bright), var(--amber));
  border-color: var(--amber-dim);
  box-shadow: var(--shadow-2), 0 0 26px -3px var(--amber-glow);
  animation: pulse 1.4s ease-in-out infinite;
}

/* Loading sounds: an amber spinner instead of the play glyph. The button is
   disabled while loading, so override the dimming so it still reads as "working"
   (higher specificity than .play:disabled). */
.play.is-loading,
.play.is-loading:disabled {
  color: var(--amber-bright);
  filter: none;
}

.play__spinner {
  transform-origin: center;
  animation: play-spin 0.72s linear infinite;
}

@keyframes play-spin {
  to {
    transform: rotate(360deg);
  }
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

.metro-btn:active:not(:disabled) {
  transform: translateY(1px);
}

.metro-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.metro-btn.is-on {
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), 0 0 16px -5px var(--amber-glow), inset 0 0 0 1px rgba(255, 157, 60, 0.3);
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
    flex-direction: column;
    align-items: stretch;
  }
  .cluster {
    justify-content: center;
    flex-wrap: wrap;
  }
  .metro-panel {
    flex-direction: column;
    align-items: stretch;
  }
  .metro-panel__controls {
    margin-left: 0;
    justify-content: center;
  }
  .volume {
    flex: 1 1 140px;
  }
  .volume__range {
    flex: 1 1 auto;
    width: auto;
    min-width: 0;
  }
}
</style>
