<script setup lang="ts">
import {
  Articulation,
  Beam,
  Formatter,
  GraceNote,
  GraceNoteGroup,
  Modifier,
  Renderer,
  Stave,
  StaveNote,
} from 'vexflow'
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{
  sticking: ('L' | 'R')[]
  accents: boolean[]
  grace: number[]
  clef?: boolean
}>()

const host = ref<HTMLDivElement | null>(null)

function render(): void {
  const el = host.value
  if (el === null) return
  el.innerHTML = ''

  const n = props.sticking.length
  const withClef = props.clef !== false
  const totalGrace = props.grace.reduce((a, b) => a + b, 0)
  const clefW = withClef ? 34 : 6
  const width = clefW + n * 34 + totalGrace * 12 + 20
  const height = 72

  const renderer = new Renderer(el, Renderer.Backends.SVG)
  renderer.resize(width, height)
  const ctx = renderer.getContext()

  const stave = new Stave(4, 12, width - 8)
  if (withClef) stave.addClef('percussion')
  stave.setContext(ctx).draw()

  const notes = props.sticking.map((_hand, i) => {
    const note = new StaveNote({ keys: ['b/4'], duration: '8' })
    if (props.accents[i]) {
      note.addModifier(new Articulation('a>').setPosition(Modifier.Position.ABOVE))
    }
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
