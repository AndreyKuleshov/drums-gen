<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import GrooveScore from './GrooveScore.vue'
import ScoreView from './ScoreView.vue'
import { playPhrase, stopPhrase } from '../lib/audio'
import { playGroove, stopGroove } from '../lib/kit'
import type { Groove, Phrase } from '../types'

const props = defineProps<{
  kind: 'exercise' | 'pattern'
  pattern: unknown
  tempo?: number
  ver?: string
  rater?: string
}>()
const emit = defineEmits<{ (e: 'close'): void }>()

const playing = ref(false)
const activeStep = ref<number | null>(null)
const metronome = ref(false)

const heading = computed(() => {
  const parts: string[] = [props.kind]
  if (props.tempo) parts.push(`${props.tempo}bpm`)
  if (props.ver) parts.push(`v${props.ver}`)
  if (props.rater) parts.push(props.rater)
  return parts.join(' · ')
})

// Focus trap: keep Tab inside the dialog, restore focus to the opener on close.
const dialog = ref<HTMLElement | null>(null)
let opener: HTMLElement | null = null
function focusable(): HTMLElement[] {
  if (!dialog.value) return []
  return Array.from(
    dialog.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input, [tabindex]:not([tabindex="-1"])',
    ),
  )
}

async function play(): Promise<void> {
  playing.value = true
  const common = {
    tempoBpm: props.tempo,
    metronome: metronome.value,
    onStep: (i: number | null) => {
      activeStep.value = i
    },
    onEnd: () => {
      playing.value = false
      activeStep.value = null
    },
  }
  if (props.kind === 'pattern') {
    await playGroove(props.pattern as Groove, common)
  } else {
    await playPhrase(props.pattern as Phrase, common)
  }
}

function stop(): void {
  playing.value = false
  activeStep.value = null
  if (props.kind === 'pattern') stopGroove()
  else stopPhrase()
}

function onKey(e: KeyboardEvent): void {
  if (e.key === 'Escape') {
    emit('close')
    return
  }
  if (e.key !== 'Tab') return
  const items = focusable()
  if (items.length === 0) return
  const first = items[0]
  const last = items[items.length - 1]
  const active = document.activeElement as HTMLElement | null
  if (e.shiftKey && (active === first || !dialog.value?.contains(active))) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && (active === last || !dialog.value?.contains(active))) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(async () => {
  opener = document.activeElement as HTMLElement | null
  window.addEventListener('keydown', onKey)
  await nextTick()
  focusable()[0]?.focus()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  stop()
  opener?.focus()
})
</script>

<template>
  <Teleport to="body">
    <div class="preview__backdrop" @click="emit('close')" />
    <div ref="dialog" class="preview" role="dialog" aria-modal="true" aria-labelledby="preview-heading">
      <h3 id="preview-heading" class="preview__title">{{ heading }}</h3>
      <div class="preview__score score" role="img" :aria-label="`Notation for ${heading}`">
        <GrooveScore v-if="kind === 'pattern'" :groove="(pattern as Groove)" :active-step="activeStep" />
        <ScoreView v-else :phrase="(pattern as Phrase)" :active-step="activeStep" />
      </div>
      <div class="preview__actions">
        <label class="preview__metro">
          <input v-model="metronome" type="checkbox" data-test="metronome" />
          metronome
        </label>
        <button v-if="!playing" type="button" class="ratebtn" @click="play">▶ Play</button>
        <button v-else type="button" class="ratebtn" @click="stop">■ Stop</button>
        <button type="button" class="ratebtn" @click="emit('close')">Close</button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.preview__backdrop {
  position: fixed; inset: 0; z-index: 80; background: rgba(8, 6, 4, 0.72); backdrop-filter: blur(2px);
}
.preview {
  position: fixed; z-index: 81; top: 50%; left: 50%; transform: translate(-50%, -50%);
  width: min(94vw, 820px); padding: 18px; border-radius: var(--r-lg); border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--panel)); box-shadow: var(--shadow-3);
}
.preview__title {
  margin: 0 0 12px;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.05em;
  color: var(--text-dim);
  text-transform: uppercase;
}
.preview__score { background: var(--screen); border-radius: var(--r-md); overflow-x: auto; padding: 8px; }
.preview__actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.preview__metro { display: inline-flex; align-items: center; gap: 6px; margin-right: auto; font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-dim); }
.ratebtn {
  padding: 7px 14px; border-radius: var(--r-md); border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel)); color: var(--text-dim);
  font-family: var(--font-mono); font-size: 0.72rem; cursor: pointer;
}
.ratebtn:hover { color: var(--amber-bright); }
</style>
