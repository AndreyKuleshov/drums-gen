<script setup lang="ts">
import { ref } from 'vue'

import GenerationForm from './components/GenerationForm.vue'
import PlayerControls from './components/PlayerControls.vue'
import ScoreView from './components/ScoreView.vue'
import type { Phrase } from './types'

const phrase = ref<Phrase | null>(null)
const activeStep = ref<number | null>(null)
const tempo = ref(100)
const booting = ref(false)
let bootTimer: ReturnType<typeof setTimeout> | null = null

function onGenerated(next: Phrase): void {
  activeStep.value = null
  phrase.value = next
  // Brief "display power-on" glow when new notation lands.
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
          <span class="led" :class="{ 'led--on': true }" aria-hidden="true" />
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
      </section>

      <PlayerControls :phrase="phrase" :tempo="tempo" @step="activeStep = $event" />

      <GenerationForm v-model:tempo="tempo" @update:phrase="onGenerated" />
    </div>
  </main>
</template>

<style scoped>
.stage {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: clamp(16px, 4vw, 56px);
}

.console {
  width: 100%;
  max-width: 1040px;
  background: linear-gradient(180deg, var(--panel), var(--chassis));
  border: 1px solid var(--edge);
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-3), var(--inset);
  padding: clamp(16px, 2.4vw, 28px);
  display: flex;
  flex-direction: column;
  gap: clamp(16px, 2vw, 22px);
}

.console__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand__mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: var(--r-md);
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  border: 1px solid var(--edge);
  box-shadow: var(--shadow-1), inset 0 1px 0 rgba(239, 231, 216, 0.08);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.85rem;
  letter-spacing: -0.02em;
  color: var(--amber);
}

.brand__name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(1.05rem, 2.4vw, 1.4rem);
  letter-spacing: -0.02em;
}

.brand__meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand__model {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  color: var(--text-faint);
}

.led {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--amber-dim);
}

.led--on {
  background: var(--amber);
  box-shadow: 0 0 10px 1px var(--amber-glow);
}

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
  background:
    linear-gradient(180deg, #fbf6ec, var(--screen));
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
