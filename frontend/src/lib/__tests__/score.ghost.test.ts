import { describe, expect, it } from 'vitest'

import { barToNoteSpecs } from '../score'
import type { Bar } from '../../types'

const bar: Bar = {
  time_sig: { num: 4, den: 4 },
  strokes: [
    { duration: '1/16', hand: 'R', accent: true, ghost: false, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
    { duration: '1/16', hand: 'L', accent: false, ghost: true, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
  ],
}

describe('barToNoteSpecs', () => {
  it('carries the ghost flag through to the note spec', () => {
    const specs = barToNoteSpecs(bar)
    expect(specs[0].ghost).toBe(false)
    expect(specs[1].ghost).toBe(true)
  })
})
