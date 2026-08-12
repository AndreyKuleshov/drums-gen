<script setup lang="ts">
import {
  Articulation,
  Beam,
  Dot,
  Formatter,
  Fraction as VFraction,
  GraceNote,
  GraceNoteGroup,
  Modifier,
  Renderer,
  Stave,
  StaveNote,
  Voice,
} from 'vexflow'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { parseFraction } from '../lib/audio'
import { combinedOnsetsWhole } from '../lib/kit'
import type { GrooveBar, Hit } from '../types'
import type { Groove } from '../types'

const props = defineProps<{ groove: Groove; activeStep?: number | null }>()
const container = ref<HTMLDivElement | null>(null)

// Kit staff positions and notehead glyphs (percussion clef, stems up = hands).
const HIHAT_KEY = 'g/5/x2'
const SNARE_KEY = 'c/5'
const KICK_KEY = 'f/4'
const TOM_KEY: Record<string, string> = {
  tom_high: 'e/5',
  tom_mid: 'd/5',
  tom_low: 'a/4',
}
const CELL = 1 / 32 // notation grid (every onset lands here — supports 32nds in fills)

// Layout (px). Bars wrap into rows fitted to the container so the phrase never
// scrolls horizontally.
const LEFT = 10
const TOP = 52 // headroom above the stave for accents + the R/L sticking line
const ROW_HEIGHT = 160
const CLEF_W = 52
// Bars are sized by the width VexFlow needs for their notes (measured per bar), so
// notes never spill past the barline; the whole SVG then scales to fit the screen.
const MIN_BAR_W = 112
const DEFAULT_LINE_W = 1000

// Cell-count -> note tokens. Power-of-two durations ONLY: VexFlow's Dot modifier
// is visual and does NOT change a tickable's duration, so dotted values would
// mis-place every following note. A 6-cell span becomes quarter + eighth, etc.
const TABLE: [number, string, number][] = [
  [32, 'w', 0],
  [16, 'h', 0],
  [8, 'q', 0],
  [4, '8', 0],
  [2, '16', 0],
  [1, '32', 0],
]

function decompose(cells: number): { code: string; dots: number }[] {
  const out: { code: string; dots: number }[] = []
  let rem = cells
  while (rem > 0) {
    const t = TABLE.find(([c]) => c <= rem) ?? [1, '16', 0]
    out.push({ code: t[1], dots: t[2] })
    rem -= t[0]
  }
  return out
}

function barCells(bar: GrooveBar): number {
  return Math.round(bar.time_sig.num / bar.time_sig.den / CELL)
}

// For each playback step (a unique onset across both voices), the SVG elements of
// every note sounding then — so simultaneous hits highlight together.
let stepEls: SVGElement[][] = []

// A drawn tickable plus the onset cell it sounds on (null for a rest) and, for a
// hands note, the sticking hand (drawn later on a uniform line).
interface NoteItem {
  note: StaveNote
  cell: number | null
  hand?: 'R' | 'L' | null
  accent?: boolean
}

function makeRest(code: string, dots: number, up: boolean): NoteItem {
  const note = new StaveNote({ keys: ['b/4'], duration: `${code}r`, stem_direction: up ? 1 : -1 })
  // A dotted rest (e.g. dotted-quarter = 6 sixteenths) MUST carry its dots, or its
  // duration is short and every following note shifts earlier.
  for (let d = 0; d < dots; d++) Dot.buildAndAttach([note])
  return { note, cell: null }
}

interface CellInfo {
  keys: string[]
  ghostIdx: number[]
  open: boolean
  accent: boolean
  hand: 'R' | 'L' | null
  art: string
}

// Sticking is printed only for the MELODIC hand (snare / toms) — the hi-hat is a
// timekeeping ostinato, so labelling every hat with its (right) hand just reads as
// a max-two-rule violation on a groove. Pure hi-hat cells get no letter.
function stickingHand(hits: Hit[]): 'R' | 'L' | null {
  const lead = hits.find(
    (h) => h.surface !== 'hihat' && h.surface !== 'hihat_open' && h.hand,
  )
  return lead?.hand ?? null
}

function keysFor(hits: Hit[]): CellInfo {
  const keys: string[] = []
  const ghostIdx: number[] = []
  let open = false
  let accent = false
  const hasHat = hits.some((h) => h.surface === 'hihat' || h.surface === 'hihat_open')
  if (hasHat) keys.push(HIHAT_KEY)
  if (hits.some((h) => h.surface === 'hihat_open')) open = true
  const snare = hits.find((h) => h.surface === 'snare')
  if (snare) {
    keys.push(SNARE_KEY)
    if (snare.ghost) ghostIdx.push(keys.length - 1)
  }
  for (const surface of ['tom_low', 'tom_high', 'tom_mid']) {
    const tom = hits.find((h) => h.surface === surface)
    if (tom) {
      keys.push(TOM_KEY[surface])
      if (tom.ghost) ghostIdx.push(keys.length - 1)
    }
  }
  if (hits.some((h) => h.accent)) accent = true
  const ornamented = hits.find((h) => h.articulation && h.articulation !== 'normal')
  return {
    keys,
    ghostIdx,
    open,
    accent,
    hand: stickingHand(hits),
    art: ornamented?.articulation ?? 'normal',
  }
}

function buildHandsVoice(bar: GrooveBar, cells: number): NoteItem[] {
  const byCell = new Map<number, Hit[]>()
  for (const h of bar.hands) {
    const c = Math.round(parseFraction(h.onset) / CELL)
    byCell.set(c, [...(byCell.get(c) ?? []), h])
  }
  const cellsWithHits = [...byCell.keys()].sort((a, b) => a - b)
  const items: NoteItem[] = []
  let pos = 0
  for (let i = 0; i < cellsWithHits.length; i++) {
    const c = cellsWithHits[i]
    if (c > pos) for (const t of decompose(c - pos)) items.push(makeRest(t.code, t.dots, true))
    const next = i + 1 < cellsWithHits.length ? cellsWithHits[i + 1] : cells
    const [head, ...tail] = decompose(next - c)
    const { keys, ghostIdx, open, accent, hand, art } = keysFor(byCell.get(c) ?? [])
    const note = new StaveNote({ keys, duration: head.code, stem_direction: 1 })
    for (let d = 0; d < head.dots; d++) Dot.buildAndAttach([note])
    // Flam = one slashed grace; drag = two beamed graces — on the same drum.
    if (art === 'flam' || art === 'drag') {
      const n = art === 'drag' ? 2 : 1
      const graces = Array.from(
        { length: n },
        () => new GraceNote({ keys: [keys[0] ?? SNARE_KEY], duration: '16', slash: n === 1 }),
      )
      const group = new GraceNoteGroup(graces, false)
      if (n === 2) group.beamNotes()
      note.addModifier(group, 0)
    }
    // Open hi-hat: the standard open-circle symbol above the note (closed = plain x).
    if (open) note.addModifier(new Articulation('ao').setPosition(Modifier.Position.ABOVE))
    for (const gi of ghostIdx) note.setKeyStyle(gi, { fillStyle: '#8a7d68', strokeStyle: '#8a7d68' })
    // Accents (>) and sticking (R/L) are drawn manually after layout on uniform
    // lines — not as per-note modifiers, which would jump with stem heights.
    items.push({ note, cell: c, hand, accent })
    for (const t of tail) items.push(makeRest(t.code, t.dots, true))
    pos = next
  }
  if (pos < cells) for (const t of decompose(cells - pos)) items.push(makeRest(t.code, t.dots, true))
  return items
}

function buildFeetVoice(bar: GrooveBar, cells: number): NoteItem[] {
  const byCell = new Map<number, Hit[]>()
  for (const h of bar.feet) {
    const c = Math.round(parseFraction(h.onset) / CELL)
    byCell.set(c, [...(byCell.get(c) ?? []), h])
  }
  const cellsWithHits = [...byCell.keys()].sort((a, b) => a - b)
  const items: NoteItem[] = []
  let pos = 0
  for (let i = 0; i < cellsWithHits.length; i++) {
    const c = cellsWithHits[i]
    if (c > pos) for (const t of decompose(c - pos)) items.push(makeRest(t.code, t.dots, false))
    const next = i + 1 < cellsWithHits.length ? cellsWithHits[i + 1] : cells
    const cellHits = byCell.get(c) ?? []
    // Notate the kick at its own (short) duration, then rest to the next onset —
    // so a lone downbeat kick reads as a note + rests, not a whole note.
    const gap = next - c
    const holdCells = Math.min(
      gap,
      Math.max(1, ...cellHits.map((h) => Math.round(parseFraction(h.duration) / CELL))),
    )
    const [head, ...tail] = decompose(holdCells)
    const note = new StaveNote({ keys: [KICK_KEY], duration: head.code, stem_direction: -1 })
    for (let d = 0; d < head.dots; d++) Dot.buildAndAttach([note])
    if (cellHits.some((h) => h.accent)) {
      note.addModifier(new Articulation('a>').setPosition(Modifier.Position.BELOW))
    }
    items.push({ note, cell: c })
    for (const t of tail) items.push(makeRest(t.code, t.dots, false))
    for (const t of decompose(gap - holdCells)) items.push(makeRest(t.code, t.dots, false))
    pos = next
  }
  if (pos < cells) for (const t of decompose(cells - pos)) items.push(makeRest(t.code, t.dots, false))
  return items
}

interface BarLayout {
  bar: GrooveBar
  cells: number
  start: number
  top: number
  width: number
  firstInRow: boolean
}

const INNER_PAD = 22 // gap between the last note and the right barline

interface BarBuilt {
  bar: GrooveBar
  hands: NoteItem[]
  feet: NoteItem[]
  handsVoice: Voice
  feetVoice: Voice
  beams: Beam[]
  minW: number // the width VexFlow actually needs for the notes (no clef)
}

function layoutBars(
  built: BarBuilt[],
  lineWidth: number,
): { rows: BarLayout[]; height: number; contentW: number } {
  const rows: BarLayout[] = []
  let x = LEFT
  let top = TOP
  let firstInRow = true
  let contentW = 0

  const widthOf = (i: number, first: boolean): number => {
    const clef = first ? CLEF_W : 0
    return Math.max(MIN_BAR_W + clef, built[i].minW + clef + INNER_PAD)
  }

  built.forEach((b, i) => {
    if (!firstInRow && x + widthOf(i, false) > lineWidth) {
      top += ROW_HEIGHT
      x = LEFT
      firstInRow = true
    }
    const width = widthOf(i, firstInRow)
    rows.push({ bar: b.bar, cells: barCells(b.bar), start: x, top, width, firstInRow })
    x += width
    contentW = Math.max(contentW, x)
    firstInRow = false
  })
  return { rows, height: top + ROW_HEIGHT, contentW: contentW + LEFT }
}

function render(): void {
  const host = container.value
  if (host === null) return
  host.innerHTML = ''

  const bars = props.groove.bars
  // Step timeline shared with playback: each unique onset (both voices) is a step.
  const steps = combinedOnsetsWhole(props.groove)
  const stepIndex = new Map<number, number>()
  steps.forEach((onWhole, i) => stepIndex.set(Math.round(onWhole / CELL), i))
  stepEls = steps.map(() => [])

  // Measure the PARENT's width, not the host's — the host stretches to its own SVG
  // content (flex child), which would feed a stale wide width back in and overflow.
  const parentW = host.parentElement?.clientWidth ?? host.clientWidth
  const avail = parentW - 20
  const lineWidth = avail > 60 ? avail : DEFAULT_LINE_W

  const groups = [new VFraction(1, 4)]
  // Pass 1: build each bar's voices + beams and measure the width VexFlow really
  // needs for the notes — so the stave is never too narrow and notes never spill
  // past the barline.
  const built: BarBuilt[] = bars.map((bar) => {
    const cells = barCells(bar)
    const hands = buildHandsVoice(bar, cells)
    const feet = buildFeetVoice(bar, cells)
    const mk = (items: NoteItem[]): Voice =>
      new Voice({ num_beats: bar.time_sig.num, beat_value: bar.time_sig.den })
        .setStrict(false)
        .addTickables(items.map((it) => it.note))
    const handsVoice = mk(hands)
    const feetVoice = mk(feet)
    const beams = [
      ...Beam.generateBeams(hands.map((it) => it.note), {
        groups,
        stem_direction: 1,
        maintain_stem_directions: true,
      }),
      ...Beam.generateBeams(feet.map((it) => it.note), {
        groups,
        stem_direction: -1,
        maintain_stem_directions: true,
      }),
    ]
    const minW = Math.ceil(
      new Formatter()
        .joinVoices([handsVoice, feetVoice])
        .preCalculateMinTotalWidth([handsVoice, feetVoice]),
    )
    return { bar, hands, feet, handsVoice, feetVoice, beams, minW }
  })

  const { rows, height, contentW } = layoutBars(built, lineWidth)
  const renderer = new Renderer(host, Renderer.Backends.SVG)
  renderer.resize(Math.max(lineWidth, contentW), height)
  const ctx = renderer.getContext()

  // Pass 2: draw each bar at its laid-out position, formatting notes to the width
  // they need (so they fit inside the stave).
  let elapsedWhole = 0
  rows.forEach(({ bar, start, top, width, firstInRow }, i) => {
    const b = built[i]
    const barStart = elapsedWhole
    const stave = new Stave(start, top, width)
    if (firstInRow) {
      stave.addClef('percussion').addTimeSignature(`${bar.time_sig.num}/${bar.time_sig.den}`)
    }
    stave.setContext(ctx).draw()

    new Formatter()
      .joinVoices([b.handsVoice, b.feetVoice])
      .format([b.handsVoice, b.feetVoice], width - (firstInRow ? CLEF_W : 0) - INNER_PAD)
    b.handsVoice.draw(ctx, stave)
    b.feetVoice.draw(ctx, stave)
    b.beams.forEach((bm) => bm.setContext(ctx).draw())

    // Accents (>) and sticking (R/L) drawn manually on two uniform lines above the
    // staff, so neither jumps with individual stem/beam heights.
    const played = b.hands.filter((it) => it.cell !== null)
    if (played.length > 0) {
      const topY = Math.min(...played.map((it) => it.note.getStemExtents().topY))
      const accentY = topY - 9
      const stickY = topY - 24
      ctx.setFont('Georgia, serif', 15, 'bold')
      for (const it of played) {
        if (it.accent) ctx.fillText('>', it.note.getAbsoluteX() - 3, accentY)
      }
      ctx.setFont('Georgia, serif', 13, '')
      for (const it of played) {
        if (it.hand) ctx.fillText(it.hand, it.note.getAbsoluteX() - 3, stickY)
      }
    }

    // Map every drawn note to its playback step so simultaneous hits light together.
    for (const it of [...b.hands, ...b.feet]) {
      if (it.cell === null) continue
      const idx = stepIndex.get(Math.round((barStart + it.cell * CELL) / CELL))
      const el = it.note.getSVGElement()
      if (idx !== undefined && el) stepEls[idx].push(el)
    }

    elapsedWhole += bar.time_sig.num / bar.time_sig.den
  })

  // Make the SVG responsive: a viewBox around the real rendered content, then a
  // fluid width capped at that content's natural size. On a narrow phone it scales
  // DOWN to the container (VexFlow won't compress notes, so this is the only way to
  // guarantee a dense bar fits); on desktop it never scales UP past natural size.
  const svgEl = host.querySelector('svg') as SVGSVGElement | null
  if (svgEl !== null) {
    const bb = svgEl.getBBox()
    const pad = 6
    const vbW = Math.ceil(bb.width + pad * 2)
    const vbH = Math.ceil(bb.height + pad * 2)
    svgEl.setAttribute('viewBox', `${bb.x - pad} ${bb.y - pad} ${vbW} ${vbH}`)
    svgEl.setAttribute('preserveAspectRatio', 'xMinYMin meet')
    svgEl.removeAttribute('height')
    svgEl.style.width = '100%'
    svgEl.style.maxWidth = `${vbW}px`
    svgEl.style.height = 'auto'
    svgEl.style.display = 'block'
  }

  highlight(props.activeStep ?? null)
}

const ACTIVE = 'note-active'
let litEls: SVGElement[] = []
function highlight(index: number | null): void {
  for (const el of litEls) el.classList.remove(ACTIVE)
  litEls = []
  if (index === null || index === undefined) return
  const els = stepEls[index]
  if (els) {
    for (const el of els) el.classList.add(ACTIVE)
    litEls = els
  }
}

let raf = 0
function onResize(): void {
  cancelAnimationFrame(raf)
  raf = requestAnimationFrame(render)
}

onMounted(() => {
  render()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
watch(() => props.groove, render, { deep: true })
watch(() => props.activeStep, (i) => highlight(i ?? null))
</script>

<template>
  <div ref="container" class="groovescore" />
</template>

<style scoped>
.groovescore {
  width: 100%;
  min-width: 0; /* allow the flex child to shrink to its parent instead of its SVG */
  max-width: 100%;
  padding: 6px 10px 14px;
  overflow: hidden;
}
</style>
