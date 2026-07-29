<script setup lang="ts">
import {
  Annotation,
  AnnotationVerticalJustify,
  Articulation,
  Formatter,
  Modifier,
  Renderer,
  Stave,
  StaveNote,
  Tuplet,
} from 'vexflow'
import { ref, watch } from 'vue'

import { barToNoteSpecs, isTripletDuration } from '../lib/score'
import type { Phrase } from '../types'

const props = defineProps<{ phrase: Phrase | null }>()
const container = ref<HTMLDivElement | null>(null)

function render(phrase: Phrase): void {
  const host = container.value
  if (host === null) return
  host.innerHTML = ''
  const renderer = new Renderer(host, Renderer.Backends.SVG)
  const width = 260 * phrase.bars.length
  renderer.resize(width, 160)
  const context = renderer.getContext()

  phrase.bars.forEach((bar, index) => {
    const stave = new Stave(10 + index * 260, 40, 250)
    if (index === 0) {
      stave.addClef('percussion').addTimeSignature(`${bar.time_sig.num}/${bar.time_sig.den}`)
    }
    stave.setContext(context).draw()

    const notes = barToNoteSpecs(bar).map((spec) => {
      const note = new StaveNote({ keys: ['b/4'], duration: spec.duration })
      note.addModifier(
        new Annotation(spec.sticking).setVerticalJustification(AnnotationVerticalJustify.BOTTOM),
      )
      if (spec.accent) {
        note.addModifier(new Articulation('a>').setPosition(Modifier.Position.ABOVE))
      }
      return note
    })
    Formatter.FormatAndDraw(context, stave, notes)

    const triplet = bar.strokes.length > 0 && isTripletDuration(bar.strokes[0].duration)
    if (triplet) {
      for (let i = 0; i + 3 <= notes.length; i += 3) {
        const tuplet = new Tuplet(notes.slice(i, i + 3), { num_notes: 3, notes_occupied: 2 })
        tuplet.setContext(context).draw()
      }
    }
  })
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
  <div ref="container" />
</template>
