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
const TOP = 40
const HEIGHT = 190
const PX_PER_NOTE = 30
const CLEF_TIME_WIDTH = 60
const MIN_BAR_WIDTH = 160

function render(phrase: Phrase): void {
  const host = container.value
  if (host === null) return
  host.innerHTML = ''
  const renderer = new Renderer(host, Renderer.Backends.SVG)
  const context = renderer.getContext()

  // First pass: size each bar to its note count so nothing gets clipped.
  let x = LEFT_MARGIN
  const layout = phrase.bars.map((bar, index) => {
    const extra = index === 0 ? CLEF_TIME_WIDTH : 0
    const width = Math.max(MIN_BAR_WIDTH, bar.strokes.length * PX_PER_NOTE + extra)
    const start = x
    x += width
    return { bar, index, start, width }
  })
  renderer.resize(x + LEFT_MARGIN, HEIGHT)

  for (const { bar, index, start, width } of layout) {
    const stave = new Stave(start, TOP, width)
    if (index === 0) {
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
  overflow-x: auto;
  max-width: 100%;
}
</style>
