import { describe, expect, it } from 'vitest'

import { scheduleTimes } from '../audio'
import type { Phrase } from '../../types'

const phrase: Phrase = {
  time_sig: { num: 4, den: 4 },
  tempo_bpm: 120,
  subdivision: '1/16',
  accent_mode: 'rudiment',
  bars: [
    {
      time_sig: { num: 4, den: 4 },
      strokes: [
        { duration: '1/16', hand: 'R', accent: true, ghost: false, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
        { duration: '1/16', hand: 'L', accent: false, ghost: true, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
        { duration: '1/16', hand: 'R', accent: false, ghost: false, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
      ],
    },
  ],
}

describe('scheduleTimes velocity', () => {
  it('is loud for accents, soft for ghosts, medium otherwise', () => {
    const [acc, ghost, normal] = scheduleTimes(phrase)
    expect(acc.velocity).toBe(1.0)
    expect(ghost.velocity).toBe(0.15)
    expect(normal.velocity).toBe(0.6)
  })
})
