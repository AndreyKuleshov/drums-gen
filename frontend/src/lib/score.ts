import type { Bar } from '../types'

const DURATION_MAP: Record<string, string> = {
  '1/1': 'w',
  '1/2': 'h',
  '1/4': 'q',
  '1/8': '8',
  '1/16': '16',
  '1/32': '32',
  '1/12': '8', // eighth-note triplet base
  '1/24': '16', // sixteenth-note triplet base
  '1/6': 'q', // quarter-note triplet base
}

const TRIPLET_DURATIONS = new Set(['1/6', '1/12', '1/24'])

export function isTripletDuration(subdivision: string): boolean {
  return TRIPLET_DURATIONS.has(subdivision)
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
  /** Rudiment-instance index carried from the backend; used to beam by phrase. */
  group: number
}

export function barToNoteSpecs(bar: Bar): NoteSpec[] {
  return bar.strokes.map((s) => ({
    duration: vexDuration(s.duration),
    accent: s.accent,
    sticking: s.hand,
    group: s.group,
  }))
}

/** VexFlow duration codes that can be joined by a beam (eighth and shorter). */
const BEAMABLE = new Set(['8', '16', '32'])

/**
 * Compute which note indices should be beamed together: maximal runs of
 * consecutive beamable notes that share the same rudiment group. Runs shorter
 * than two notes are dropped (a beam needs at least two notes).
 */
export function beamGroups(specs: NoteSpec[]): number[][] {
  const groups: number[][] = []
  let current: number[] = []
  let currentGroup: number | null = null

  const flush = (): void => {
    if (current.length >= 2) groups.push(current)
    current = []
    currentGroup = null
  }

  specs.forEach((spec, index) => {
    if (!BEAMABLE.has(spec.duration)) {
      flush()
      return
    }
    if (currentGroup === spec.group) {
      current.push(index)
    } else {
      flush()
      current = [index]
      currentGroup = spec.group
    }
  })
  flush()
  return groups
}
