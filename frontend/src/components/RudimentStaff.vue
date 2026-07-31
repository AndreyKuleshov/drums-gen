<script setup lang="ts">
import { Beam, Formatter, GraceNote, GraceNoteGroup, Renderer, Stave, StaveNote } from 'vexflow'
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{
  sticking: ('L' | 'R')[]
  accents: boolean[]
  grace: number[]
  clef?: boolean
}>()

const host = ref<HTMLDivElement | null>(null)

// Mirrors the generator's ScoreView notation: accents drawn manually as ">"
// above the stems, and the sticking drawn manually just under each notehead so
// the letters line up with the notes and the card stays compact (a VexFlow
// BOTTOM annotation anchors ~100px below the stave, forcing oversized boxes).
function render(): void {
  const el = host.value
  if (el === null) return
  el.innerHTML = ''

  const n = props.sticking.length
  if (n === 0) return
  const withClef = props.clef !== false
  const totalGrace = props.grace.reduce((a, b) => a + b, 0)

  const PX_PER_NOTE = 40
  const clefW = withClef ? 42 : 10
  const width = clefW + n * PX_PER_NOTE + totalGrace * 14 + 24

  const renderer = new Renderer(el, Renderer.Backends.SVG)
  // Provisional height; grown to fit the sticking row once the notes are laid
  // out (percussion b/4 sits low, so its exact y isn't known until drawn).
  renderer.resize(width, 110)
  const ctx = renderer.getContext()

  const stave = new Stave(4, 28, width - 8)
  if (withClef) stave.addClef('percussion')
  stave.setContext(ctx).draw()

  const notes = props.sticking.map((_hand, i) => {
    const note = new StaveNote({ keys: ['b/4'], duration: '8' })
    const g = props.grace[i]
    if (g > 0) {
      const graces = Array.from(
        { length: g },
        () => new GraceNote({ keys: ['b/4'], duration: '16', slash: g === 1 }),
      )
      const group = new GraceNoteGroup(graces, false)
      if (g === 2) group.beamNotes()
      note.addModifier(group, 0)
    }
    return note
  })

  const beams = n >= 2 ? [new Beam(notes)] : []
  Formatter.FormatAndDraw(ctx, stave, notes)
  beams.forEach((b) => b.setContext(ctx).draw())

  // Accents above the stems (matches the generator's notation).
  const accentIdx = props.accents.flatMap((a, i) => (a ? [i] : []))
  if (accentIdx.length > 0) {
    const stemTop = Math.min(...notes.map((note) => note.getStemExtents().topY))
    const accentY = stemTop - 14
    ctx.setFont('Georgia, serif', 15, 'bold')
    for (const i of accentIdx) {
      ctx.fillText('>', notes[i].getAbsoluteX() - 3, accentY)
    }
  }

  // Sticking just under each notehead, aligned to the note's x.
  const headY = Math.max(...notes.map((note) => note.getYs()[0]))
  const stickY = headY + 26
  ctx.setFont('Georgia, serif', 13, 'normal')
  props.sticking.forEach((hand, i) => {
    ctx.fillText(hand, notes[i].getAbsoluteX() - 3, stickY)
  })

  // Grow the SVG to reveal the sticking row (resize keeps drawn content as-is).
  renderer.resize(width, Math.ceil(stickY) + 12)
}

onMounted(render)
watch(() => props.sticking, render, { deep: true })
</script>

<template>
  <div ref="host" class="rudstaff" />
</template>

<style scoped>
.rudstaff {
  display: inline-block;
  border-radius: var(--r-sm);
  background: linear-gradient(180deg, #fbf6ec, var(--screen));
  border: 1px solid var(--screen-edge);
  box-shadow: inset 0 1px 6px rgba(120, 96, 60, 0.16);
  padding: 2px 4px;
  line-height: 0;
}
</style>
