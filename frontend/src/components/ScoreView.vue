<script setup lang="ts">
import {
  Annotation,
  AnnotationVerticalJustify,
  Beam,
  Formatter,
  GraceNote,
  GraceNoteGroup,
  Renderer,
  Stave,
  StaveNote,
  Tuplet,
} from 'vexflow'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { barToNoteSpecs, beamGroups, isTripletDuration } from '../lib/score'
import type { Phrase } from '../types'

const props = defineProps<{
  phrase: Phrase | null
  activeStep?: number | null
  /** Make notes clickable (Patterns 2.0 editor); emits `note-click` with the
   * global stroke index and the note's screen position. */
  editable?: boolean
}>()
const emit = defineEmits<{
  (e: 'note-click', payload: { index: number; x: number; y: number }): void
}>()
const container = ref<HTMLDivElement | null>(null)

// SVG <g> element for each note, in global order, for playback highlighting.
let noteEls: (SVGElement | undefined)[] = []

// Layout constants (px).
const LEFT_MARGIN = 10
// Extra headroom above the stave leaves room for the block brackets + labels
// (Patterns 2.0) that sit above the accent row.
const TOP = 46
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

function layoutBars(
  phrase: Phrase,
  lineWidth: number,
  pxPerNote: number,
): { rows: BarLayout[]; height: number } {
  const rows: BarLayout[] = []
  let x = LEFT_MARGIN
  let top = TOP
  let firstInRow = true

  // A bar must never be forced wider than the line (keeps dense bars on-screen
  // on narrow phones); the clef/time only claim space when they actually fit.
  const barWidth = (bar: Phrase['bars'][number], first: boolean): number => {
    const clef = first ? CLEF_TIME_WIDTH : 0
    const natural = bar.strokes.length * pxPerNote + clef
    const min = Math.min(MIN_BAR_WIDTH + clef, lineWidth - LEFT_MARGIN * 2)
    return Math.min(Math.max(min, natural), lineWidth - LEFT_MARGIN * 2)
  }

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

  // Subtract the container's own horizontal padding so the SVG fits its content
  // box (otherwise the right edge is clipped by the padding).
  const avail = host.clientWidth - 20
  const lineWidth = avail > 2 * MIN_BAR_WIDTH ? avail : DEFAULT_LINE_WIDTH
  // Shrink note spacing so the densest bar fits the width (portrait phones).
  const maxNotes = Math.max(1, ...phrase.bars.map((b) => b.strokes.length))
  const usable = lineWidth - LEFT_MARGIN * 2 - CLEF_TIME_WIDTH
  const pxPerNote = Math.max(12, Math.min(PX_PER_NOTE, usable / maxNotes))
  const { rows, height } = layoutBars(phrase, lineWidth, pxPerNote)
  renderer.resize(lineWidth, height)
  noteEls = []

  for (const { bar, start, top, width, firstInRow } of rows) {
    const stave = new Stave(start, top, width)
    if (firstInRow) {
      stave.addClef('percussion').addTimeSignature(`${bar.time_sig.num}/${bar.time_sig.den}`)
    }
    stave.setContext(context).draw()

    const specs = barToNoteSpecs(bar)
    const notes = specs.map((spec) => {
      const note = new StaveNote({ keys: ['b/4'], duration: spec.duration })
      const label = spec.ghost ? spec.sticking.toLowerCase() : spec.sticking
      note.addModifier(
        new Annotation(label).setVerticalJustification(AnnotationVerticalJustify.BOTTOM),
      )
      // Accents are drawn manually (below) rather than as VexFlow articulations,
      // so the tuplet bracket doesn't get pushed up to clear them — that keeps
      // brackets on one level with the accents sitting above them.
      // Flam (1) / drag (2): grace notes before the main note, played by the
      // opposite hand. A single flam is slashed; a drag's two graces are beamed.
      if (spec.grace > 0) {
        const graceNotes = Array.from(
          { length: spec.grace },
          () => new GraceNote({ keys: ['b/4'], duration: '16', slash: spec.grace === 1 }),
        )
        const graceGroup = new GraceNoteGroup(graceNotes, false)
        if (spec.grace === 2) graceGroup.beamNotes()
        note.addModifier(graceGroup, 0)
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
        const tuplet = new Tuplet(notes.slice(i, i + 3), {
          num_notes: 3,
          notes_occupied: 2,
          bracketed: true,
        })
        // Raise brackets to a uniform line above the accent marks.
        tuplet.setTupletLocation(Tuplet.LOCATION_TOP)
        tuplets.push(tuplet)
      }
    }

    Formatter.FormatAndDraw(context, stave, notes)
    beams.forEach((beam) => beam.setContext(context).draw())
    tuplets.forEach((tuplet) => tuplet.setContext(context).draw())

    // Manual accents: one flat row above the (uniform) tuplet brackets.
    const accentIdx = specs.flatMap((s, i) => (s.accent ? [i] : []))
    if (accentIdx.length > 0) {
      const stemTop = Math.min(...notes.map((n) => n.getStemExtents().topY))
      const accentY = stemTop - (triplet ? 26 : 14)
      context.setFont('Georgia, serif', 15, 'bold')
      for (const i of accentIdx) {
        context.fillText('>', notes[i].getAbsoluteX() - 3, accentY)
      }
    }

    // Ghost notes: parentheses around the notehead, drawn manually (consistent
    // with the manual accent marks above) so no extra VexFlow modifier is needed.
    const ghostIdx = specs.flatMap((s, i) => (s.ghost ? [i] : []))
    if (ghostIdx.length > 0) {
      context.setFont('Georgia, serif', 15, 'normal')
      for (const i of ghostIdx) {
        const x = notes[i].getAbsoluteX()
        const y = notes[i].getYs()[0]
        context.fillText('(', x - 9, y + 5)
        context.fillText(')', x + 7, y + 5)
      }
    }

    // Block brackets (Patterns 2.0): a square bracket + label over each run of
    // notes from one vocabulary block. Labels come from the backend; singles are
    // unlabelled, so they get no bracket.
    const blockGroups: { i0: number; i1: number; label: string }[] = []
    let g = 0
    while (g < specs.length) {
      const b = specs[g].block
      if (b < 0) {
        g += 1
        continue
      }
      let j = g
      while (j + 1 < specs.length && specs[j + 1].block === b) j += 1
      if (specs[g].blockLabel) blockGroups.push({ i0: g, i1: j, label: specs[g].blockLabel })
      g = j + 1
    }
    if (blockGroups.length > 0) {
      const stemTop = Math.min(...notes.map((n) => n.getStemExtents().topY))
      const bracketY = stemTop - 30
      // Centre the bracket over the note heads (a head is ~12px wide). Drawn with
      // thin FILLED rects, not a stroked path: the notation's `path { fill }` CSS
      // force-fills any stroke-only path, collapsing it into a solid wedge/bar.
      // A continuous line with short down-hooks at each end and the label centred
      // above — a plain grouping bracket.
      const HEAD_HALF = 6
      const HOOK = 6
      const TH = 1.3
      // Reach the right hook a little past the last note so the bracket clearly
      // spans the whole group (the left hook already sits over the first note).
      const RIGHT_EXT = 11
      context.setFont('Georgia, serif', 10, 'normal')
      for (const grp of blockGroups) {
        const x0 = notes[grp.i0].getAbsoluteX() + HEAD_HALF
        const x1 = notes[grp.i1].getAbsoluteX() + HEAD_HALF + RIGHT_EXT
        context.fillRect(x0, bracketY, x1 - x0, TH) // horizontal line
        context.fillRect(x0, bracketY, TH, HOOK) // left down-hook
        context.fillRect(x1 - TH, bracketY, TH, HOOK) // right down-hook
        const w = context.measureText(grp.label).width
        context.fillText(grp.label, (x0 + x1) / 2 - w / 2, bracketY - 4)
      }
    }

    for (const note of notes) noteEls.push(note.getSVGElement())
  }

  // Focal reveal: a quick left-to-right light-up. Kept short so trailing notes
  // never linger as faint "ghosts" that read like a rendering glitch.
  noteEls.forEach((el, i) => {
    if (el === undefined) return
    el.classList.add('note-enter')
    el.style.animationDelay = `${Math.min(i * 7, 190)}ms`
    if (props.editable) {
      el.style.cursor = 'pointer'
      el.addEventListener('click', () => {
        const r = (el as unknown as SVGGraphicsElement).getBoundingClientRect()
        emit('note-click', { index: i, x: r.left + r.width / 2, y: r.top })
      })
    }
  })
}

const ACTIVE_CLASS = 'note-active'
let litEl: SVGElement | undefined

function highlight(index: number | null | undefined): void {
  litEl?.classList.remove(ACTIVE_CLASS)
  litEl = undefined
  if (index === null || index === undefined) return
  const el = noteEls[index]
  if (el) {
    el.classList.add(ACTIVE_CLASS)
    litEl = el
  }
}

// Re-render on viewport resize / rotation so note spacing re-fits the new width.
let resizeRaf = 0
function onResize(): void {
  if (props.phrase === null) return
  cancelAnimationFrame(resizeRaf)
  resizeRaf = requestAnimationFrame(() => {
    litEl = undefined
    if (props.phrase !== null) render(props.phrase)
  })
}

// Render on mount (the component is v-if'd in once a phrase exists, so the
// container is in the DOM here) and on every later phrase change. An immediate
// watch would fire synchronously before mount, when the container is still null.
onMounted(() => {
  if (props.phrase !== null) render(props.phrase)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => window.removeEventListener('resize', onResize))

watch(
  () => props.phrase,
  (phrase) => {
    litEl = undefined
    if (phrase !== null) render(phrase)
  },
)

watch(
  () => props.activeStep,
  (index) => highlight(index),
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
