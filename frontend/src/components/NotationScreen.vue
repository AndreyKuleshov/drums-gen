<script setup lang="ts">
/**
 * The shared "screen": the glass panel that displays a Groove or a Phrase, its
 * empty state, and the floating 👍/👎 rating control. Used by every mode (Studio
 * groove/exercise + Patterns 2.0) so the notation surface is one module, not one
 * per view. Pass a `groove` OR a `phrase`; provide `rate` (+ kind/params/meta) to
 * show the thumbs. Slot `below` renders inside the screen, under the glass (e.g.
 * the Studio summary plate).
 */
import { computed } from 'vue'

import GrooveScore from './GrooveScore.vue'
import RateControl from './RateControl.vue'
import ScoreView from './ScoreView.vue'
import type { Groove, Phrase } from '../types'

const props = defineProps<{
  groove?: Groove | null
  phrase?: Phrase | null
  activeStep?: number | null
  emptyText: string
  /** Notes are click-to-edit (Patterns 2.0); read-only otherwise. */
  editable?: boolean
  /** Label the hi-hat lane on the groove score. */
  labelHihat?: boolean
  /** One-shot boot glow when a fresh pattern lands. */
  boot?: boolean
  // Rating: when `rate` (the payload) and `rateKind` are set, the thumbs show.
  rate?: unknown
  rateKind?: 'exercise' | 'pattern'
  rateParams?: Record<string, unknown>
  rateSeed?: number | null
  rateMeta?: Record<string, unknown>
}>()

defineEmits<{
  (e: 'groove-note-click', payload: { bar: number; cell: number; x: number; y: number }): void
  (e: 'phrase-note-click', payload: { index: number; x: number; y: number }): void
}>()

const showRate = computed(() => props.rate != null && props.rateKind != null)
</script>

<template>
  <section class="screen" aria-label="Notation display">
    <div class="screen__glass" :class="{ 'screen__glass--boot': boot }">
      <div class="screen__stage" :class="{ 'screen__stage--inset': showRate }">
        <GrooveScore
          v-if="groove"
          :groove="groove"
          :active-step="activeStep ?? null"
          :label-hihat="labelHihat"
          :editable="editable"
          @note-click="$emit('groove-note-click', $event)"
        />
        <ScoreView
          v-else-if="phrase"
          :phrase="phrase"
          :active-step="activeStep ?? null"
          :editable="editable"
          @note-click="$emit('phrase-note-click', $event)"
        />
        <div v-else class="screen__empty">
          <span class="screen__empty-glyph" aria-hidden="true">&#9834;</span>
          <p class="screen__empty-text">{{ emptyText }}</p>
        </div>
      </div>
      <RateControl
        v-if="showRate"
        class="screen__rate"
        :pattern="rate"
        :kind="rateKind as 'exercise' | 'pattern'"
        :params="rateParams ?? {}"
        :seed="rateSeed ?? null"
        :meta="rateMeta ?? {}"
      />
    </div>
    <slot name="below" />
  </section>
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
  display: flex;
  align-items: center;
}

/* Holds the notation and fills the glass; margin (not padding) keeps the measured
   width smaller so the score renders narrower than the glass. */
.screen__stage {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
}

/* Reserve room at the top-right so notation never collides with the thumbs. */
.screen__stage--inset {
  padding-right: 96px;
}

/* Rating thumbs float in the screen's top-right corner. */
.screen__rate {
  position: absolute;
  top: 10px;
  right: 12px;
  z-index: 4;
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
</style>
