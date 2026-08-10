<script setup lang="ts">
import {
  Annotation,
  AnnotationVerticalJustify,
  Articulation,
  Beam,
  Dot,
  Formatter,
  Fraction as VFraction,
  Modifier,
  Renderer,
  Stave,
  StaveNote,
  Voice,
} from 'vexflow'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { parseFraction } from '../lib/audio'
import type { GrooveBar, Hit } from '../types'
import type { Groove } from '../types'

const props = defineProps<{ groove: Groove; activeStep?: number | null }>()
const container = ref<HTMLDivElement | null>(null)

// Kit staff positions and notehead glyphs.
const HIHAT_KEY = 'g/5/x2'
const SNARE_KEY = 'c/5'
const KICK_KEY = 'f/4'
const CELL = 1 / 16 // notation grid (every onset lands here)

const LEFT = 8
const TOP = 24
const CLEF_W = 46
const PX_PER_CELL = 15
const HEIGHT = 150

// Cell-count → note tokens (first is the note, any rest fills the remainder).
const TABLE: [number, string, number][] = [
  [16, 'w', 0],
  [12, 'h', 1],
  [8, 'h', 0],
  [6, 'q', 1],
  [4, 'q', 0],
  [3, '8', 1],
  [2, '8', 0],
  [1, '16', 0],
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

// Note SVG elements for the hands voice, in play order, for highlighting.
let handEls: (SVGElement | undefined)[] = []

function makeRest(code: string, up: boolean): StaveNote {
  return new StaveNote({ keys: ['b/4'], duration: `${code}r`, stem_direction: up ? 1 : -1 })
}

function keysFor(hits: Hit[]): { keys: string[]; ghostIdx: number[]; open: boolean; accent: boolean } {
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
  if (hits.some((h) => h.accent)) accent = true
  return { keys, ghostIdx, open, accent }
}

function buildHandsVoice(bar: GrooveBar, cells: number): StaveNote[] {
  const byCell = new Map<number, Hit[]>()
  for (const h of bar.hands) {
    const c = Math.round(parseFraction(h.onset) / CELL)
    byCell.set(c, [...(byCell.get(c) ?? []), h])
  }
  const cellsWithHits = [...byCell.keys()].sort((a, b) => a - b)
  const notes: StaveNote[] = []
  let pos = 0
  for (let i = 0; i < cellsWithHits.length; i++) {
    const c = cellsWithHits[i]
    if (c > pos) for (const t of decompose(c - pos)) notes.push(makeRest(t.code, true))
    const next = i + 1 < cellsWithHits.length ? cellsWithHits[i + 1] : cells
    const [head, ...tail] = decompose(next - c)
    const { keys, ghostIdx, open, accent } = keysFor(byCell.get(c) ?? [])
    const note = new StaveNote({ keys, duration: head.code, stem_direction: 1 })
    for (let d = 0; d < head.dots; d++) Dot.buildAndAttach([note])
    if (accent) note.addModifier(new Articulation('a>').setPosition(Modifier.Position.ABOVE))
    if (open) {
      note.addModifier(
        new Annotation('o').setVerticalJustification(AnnotationVerticalJustify.TOP),
      )
    }
    for (const gi of ghostIdx) note.setKeyStyle(gi, { fillStyle: '#8a7d68', strokeStyle: '#8a7d68' })
    notes.push(note)
    for (const t of tail) notes.push(makeRest(t.code, true))
    pos = next
  }
  if (pos < cells) for (const t of decompose(cells - pos)) notes.push(makeRest(t.code, true))
  return notes
}

function buildFeetVoice(bar: GrooveBar, cells: number): StaveNote[] {
  const byCell = new Map<number, Hit[]>()
  for (const h of bar.feet) {
    const c = Math.round(parseFraction(h.onset) / CELL)
    byCell.set(c, [...(byCell.get(c) ?? []), h])
  }
  const cellsWithHits = [...byCell.keys()].sort((a, b) => a - b)
  const notes: StaveNote[] = []
  let pos = 0
  for (let i = 0; i < cellsWithHits.length; i++) {
    const c = cellsWithHits[i]
    if (c > pos) for (const t of decompose(c - pos)) notes.push(makeRest(t.code, false))
    const next = i + 1 < cellsWithHits.length ? cellsWithHits[i + 1] : cells
    const [head, ...tail] = decompose(next - c)
    const note = new StaveNote({ keys: [KICK_KEY], duration: head.code, stem_direction: -1 })
    for (let d = 0; d < head.dots; d++) Dot.buildAndAttach([note])
    if ((byCell.get(c) ?? []).some((h) => h.accent)) {
      note.addModifier(new Articulation('a>').setPosition(Modifier.Position.BELOW))
    }
    notes.push(note)
    for (const t of tail) notes.push(makeRest(t.code, false))
    pos = next
  }
  if (pos < cells) for (const t of decompose(cells - pos)) notes.push(makeRest(t.code, false))
  return notes
}

function render(): void {
  const host = container.value
  if (host === null) return
  host.innerHTML = ''
  handEls = []

  const bars = props.groove.bars
  const barWidths = bars.map((b, i) => {
    const cells = Math.round((b.time_sig.num / b.time_sig.den) / CELL)
    return (i === 0 ? CLEF_W : 0) + cells * PX_PER_CELL + 24
  })
  const width = LEFT * 2 + barWidths.reduce((a, b) => a + b, 0)

  const renderer = new Renderer(host, Renderer.Backends.SVG)
  renderer.resize(width, HEIGHT)
  const ctx = renderer.getContext()

  let x = LEFT
  bars.forEach((bar, i) => {
    const cells = Math.round((bar.time_sig.num / bar.time_sig.den) / CELL)
    const stave = new Stave(x, TOP, barWidths[i])
    if (i === 0) {
      stave.addClef('percussion').addTimeSignature(`${bar.time_sig.num}/${bar.time_sig.den}`)
    }
    stave.setContext(ctx).draw()

    const hands = buildHandsVoice(bar, cells)
    const feet = buildFeetVoice(bar, cells)
    const mk = (notes: StaveNote[]): Voice =>
      new Voice({ num_beats: bar.time_sig.num, beat_value: bar.time_sig.den })
        .setStrict(false)
        .addTickables(notes)
    const handsVoice = mk(hands)
    const feetVoice = mk(feet)

    // Beam eighths/sixteenths in quarter-note groups (standard notation), so
    // runs beam cleanly in any meter instead of one flag per note.
    const groups = [new VFraction(1, 4)]
    const beams = [
      ...Beam.generateBeams(hands, { groups, stem_direction: 1, maintain_stem_directions: true }),
      ...Beam.generateBeams(feet, { groups, stem_direction: -1, maintain_stem_directions: true }),
    ]

    new Formatter()
      .joinVoices([handsVoice, feetVoice])
      .format([handsVoice, feetVoice], barWidths[i] - (i === 0 ? CLEF_W : 0) - 24)
    handsVoice.draw(ctx, stave)
    feetVoice.draw(ctx, stave)
    beams.forEach((b) => b.setContext(ctx).draw())

    for (const note of hands) {
      if (!note.isRest()) handEls.push(note.getSVGElement())
    }
    x += barWidths[i]
  })

  highlight(props.activeStep ?? null)
}

const ACTIVE = 'note-active'
let litEl: SVGElement | undefined
function highlight(index: number | null): void {
  litEl?.classList.remove(ACTIVE)
  litEl = undefined
  if (index === null || index === undefined) return
  const el = handEls[index]
  if (el) {
    el.classList.add(ACTIVE)
    litEl = el
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
  overflow-x: auto;
  padding: 6px 10px 14px;
}
</style>
