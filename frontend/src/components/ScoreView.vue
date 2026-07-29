<script setup lang="ts">
import {
  Annotation,
  AnnotationVerticalJustify,
  Articulation,
  Beam,
  Formatter,
  Modifier,
  Renderer,
  Stave,
  StaveNote,
  Tuplet,
} from 'vexflow'
import { ref, watch } from 'vue'

import { barToNoteSpecs, beamGroups, isTripletDuration } from '../lib/score'
import type { Phrase } from '../types'

const props = defineProps<{ phrase: Phrase | null }>()
const container = ref<HTMLDivElement | null>(null)

// Layout constants (px).
const LEFT_MARGIN = 10
const TOP = 20
const ROW_HEIGHT = 150
const PX_PER_NOTE = 30
const CLEF_TIME_WIDTH = 60
const MIN_BAR_WIDTH = 140
const DEFAULT_LINE_WIDTH = 1000

interface BarLayout {
  bar: Phrase['bars'][number]
  start: number
  top: number
  width: number
  firstInRow: boolean
}

function layoutBars(phrase: Phrase, lineWidth: number): { rows: BarLayout[]; height: number } {
  const rows: BarLayout[] = []
  let x = LEFT_MARGIN
  let top = TOP
  let firstInRow = true

  const barWidth = (bar: Phrase['bars'][number], first: boolean): number =>
    Math.max(MIN_BAR_WIDTH, bar.strokes.length * PX_PER_NOTE + (first ? CLEF_TIME_WIDTH : 0))

  for (const bar of phrase.bars) {
    // Wrap to a new row when this bar (as a continuation) would overflow the
    // line — but never wrap the first bar of a row (a single over-wide bar just
    // overflows rather than looping forever).
    if (!firstInRow && x + barWidth(bar, false) > lineWidth) {
      top += ROW_HEIGHT
      x = LEFT_MARGIN
      firstInRow = true
    }
    const width = barWidth(bar, firstInRow)
    rows.push({ bar, start: x, top, width, firstInRow })
    x += width
    firstInRow = false
  }
  return { rows, height: top + ROW_HEIGHT }
}

function render(phrase: Phrase): void {
  const host = container.value
  if (host === null) return
  host.innerHTML = ''
  const renderer = new Renderer(host, Renderer.Backends.SVG)
  const context = renderer.getContext()

  const lineWidth = host.clientWidth > 2 * MIN_BAR_WIDTH ? host.clientWidth : DEFAULT_LINE_WIDTH
  const { rows, height } = layoutBars(phrase, lineWidth)
  renderer.resize(lineWidth, height)

  for (const { bar, start, top, width, firstInRow } of rows) {
    const stave = new Stave(start, top, width)
    if (firstInRow) {
      stave.addClef('percussion').addTimeSignature(`${bar.time_sig.num}/${bar.time_sig.den}`)
    }
    stave.setContext(context).draw()

    const specs = barToNoteSpecs(bar)
    const notes = specs.map((spec) => {
      const note = new StaveNote({ keys: ['b/4'], duration: spec.duration })
      note.addModifier(
        new Annotation(spec.sticking).setVerticalJustification(AnnotationVerticalJustify.BOTTOM),
      )
      // DEBUG: group number under the sticking letter.
      note.addModifier(
        new Annotation(String(spec.group)).setVerticalJustification(
          AnnotationVerticalJustify.BOTTOM,
        ),
      )
      if (spec.accent) {
        note.addModifier(new Articulation('a>').setPosition(Modifier.Position.ABOVE))
      }
      return note
    })

    // Build beams (by rudiment group) and tuplets BEFORE formatting so the
    // notes know they are beamed (suppresses individual flags) and spaced right.
    const beams = beamGroups(specs).map((indices) => new Beam(indices.map((i) => notes[i])))

    const triplet = bar.strokes.length > 0 && isTripletDuration(bar.strokes[0].duration)
    const tuplets: Tuplet[] = []
    if (triplet) {
      for (let i = 0; i + 3 <= notes.length; i += 3) {
        tuplets.push(new Tuplet(notes.slice(i, i + 3), { num_notes: 3, notes_occupied: 2 }))
      }
    }

    Formatter.FormatAndDraw(context, stave, notes)
    beams.forEach((beam) => beam.setContext(context).draw())
    tuplets.forEach((tuplet) => tuplet.setContext(context).draw())
  }
}

watch(
  () => props.phrase,
  (phrase) => {
    if (phrase !== null) render(phrase)
  },
  { immediate: true },
)
</script>

<template>
  <div ref="container" class="score" />
</template>

<style scoped>
.score {
  width: 100%;
  overflow-x: auto;
  padding: 6px 10px 14px;
}
</style>
