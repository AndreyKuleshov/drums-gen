import { describe, expect, it } from 'vitest'

import type { Phrase } from '../../types'
import { parseFraction, scheduleTimes } from '../audio'

const phrase: Phrase = {
  time_sig: { num: 2, den: 4 },
  tempo_bpm: 60,
  subdivision: '1/4',
  accent_mode: 'rudiment',
  bars: [
    {
      time_sig: { num: 2, den: 4 },
      strokes: [
        { duration: '1/4', hand: 'R', accent: true, articulation: 'normal', surface: 'snare' },
        { duration: '1/4', hand: 'L', accent: false, articulation: 'normal', surface: 'snare' },
      ],
    },
  ],
}

describe('parseFraction', () => {
  it('parses n/d', () => {
    expect(parseFraction('1/4')).toBe(0.25)
  })
})

describe('scheduleTimes', () => {
  it('computes absolute times and velocities', () => {
    const events = scheduleTimes(phrase)
    // at 60 bpm a quarter = 1s; first stroke at t=0, second at t=1s
    expect(events.map((e) => e.timeSec)).toEqual([0, 1])
    expect(events.map((e) => e.velocity)).toEqual([1.0, 0.6])
    expect(events.map((e) => e.hand)).toEqual(['R', 'L'])
  })
})
