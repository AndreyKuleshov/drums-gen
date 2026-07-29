import type { Bar } from '../types'

const DURATION_MAP: Record<string, string> = {
  '1': 'w',
  '1/2': 'h',
  '1/4': 'q',
  '1/8': '8',
  '1/16': '16',
  '1/32': '32',
  '1/12': '8', // eighth-note triplet base
  '1/24': '16', // sixteenth-note triplet base
  '1/6': 'q', // quarter-note triplet base
}

export function vexDuration(subdivision: string): string {
  const code = DURATION_MAP[subdivision]
  if (code === undefined) {
    throw new Error(`unsupported duration: ${subdivision}`)
  }
  return code
}

export interface NoteSpec {
  duration: string
  accent: boolean
  sticking: 'L' | 'R'
}

export function barToNoteSpecs(bar: Bar): NoteSpec[] {
  return bar.strokes.map((s) => ({
    duration: vexDuration(s.duration),
    accent: s.accent,
    sticking: s.hand,
  }))
}
