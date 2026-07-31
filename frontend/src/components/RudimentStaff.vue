<script setup lang="ts">
import { Beam, Formatter, GraceNote, GraceNoteGroup, Renderer, Stave, StaveNote } from 'vexflow'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  sticking: ('L' | 'R')[]
  accents: boolean[]
  grace: number[]
  clef?: boolean
  // Absent Boolean props resolve to false in Vue, so this is phrased as an
  // opt-out: sticking shows by default; the legend passes hide-labels.
  hideLabels?: boolean
}>()

const host = ref<HTMLDivElement | null>(null)

// Mirrors the generator's ScoreView notation: accents drawn manually as ">"
// above the stems, and the sticking drawn manually just under each notehead so
// the letters line up with the notes and the card stays compact (a VexFlow
// BOTTOM annotation anchors ~100px below the stave, forcing oversized boxes).
// Note spacing shrinks to the parent width so a dense rudiment fits its card.
function render(): void {
  const el = host.value
  if (el === null) return
  el.innerHTML = ''

  const n = props.sticking.length
  if (n === 0) return
  const withClef = props.clef !== false
  const withLabels = !props.hideLabels
  const totalGrace = props.grace.reduce((a, b) => a + b, 0)

  const PX_MAX = 40
  const PX_MIN = 22
  const clefW = withClef ? 42 : 10
  const fixed = clefW + totalGrace * 14 + 24

  // Shrink per-note spacing so the staff fits the card; below PX_MIN the
  // .rudscreen wrapper scrolls rather than let notes collide.
  const avail = (el.parentElement?.clientWidth ?? 320) - 2
  // Leave headroom for the symmetric right margin added post-draw (see below).
  const budget = avail - 24
  let pxPerNote = PX_MAX
  if (fixed + n * PX_MAX > budget) pxPerNote = Math.max(PX_MIN, (budget - fixed) / n)
  const width = Math.round(fixed + n * pxPerNote)

  const renderer = new Renderer(el, Renderer.Backends.SVG)
  // Provisional height; grown to fit the content once the notes are laid out
  // (percussion b/4 sits low, so its exact y isn't known until drawn).
  renderer.resize(width, 120)
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

  const headY = Math.max(...notes.map((note) => note.getStemExtents().baseY))
  let contentBottom = headY + 16
  if (withLabels) {
    // Sticking just under each notehead, aligned to the note's x.
    const stickY = headY + 22
    ctx.setFont('Georgia, serif', 13, 'normal')
    props.sticking.forEach((hand, i) => {
      ctx.fillText(hand, notes[i].getAbsoluteX() - 3, stickY)
    })
    contentBottom = stickY + 12
  }

  // Make the right margin match the left: VexFlow leaves more space before the
  // first notehead than after the last, so pad the SVG to the mirror width.
  const firstBB = notes[0].getBoundingBox()
  const lastBB = notes[n - 1].getBoundingBox()
  const leftMargin = firstBB.getX()
  const finalWidth = Math.ceil(lastBB.getX() + lastBB.getW() + leftMargin)

  // Grow the SVG to reveal the full content (resize keeps drawn content as-is).
  renderer.resize(Math.max(width, finalWidth), Math.ceil(contentBottom))
}

let raf = 0
function scheduleRender(): void {
  cancelAnimationFrame(raf)
  raf = requestAnimationFrame(render)
}

onMounted(() => {
  render()
  window.addEventListener('resize', scheduleRender)
})
onBeforeUnmount(() => window.removeEventListener('resize', scheduleRender))
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
