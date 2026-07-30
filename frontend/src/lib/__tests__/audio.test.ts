import { describe, expect, it } from 'vitest'

import type { Phrase } from '../../types'
import { metronomeGrid, parseFraction, scheduleTimes } from '../audio'

const phrase: Phrase = {
  time_sig: { num: 2, den: 4 },
  tempo_bpm: 60,
  subdivision: '1/4',
  accent_mode: 'rudiment',
  bars: [
    {
      time_sig: { num: 2, den: 4 },
      strokes: [
        { duration: '1/4', hand: 'R', accent: true, articulation: 'normal', surface: 'snare', group: 0 },
        { duration: '1/4', hand: 'L', accent: false, articulation: 'normal', surface: 'snare', group: 1 },
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

describe('metronomeGrid', () => {
  it('one click per beat by default (4/4)', () => {
    const g = metronomeGrid(4, 4)
    expect(g.map((x) => x.level)).toEqual(['down', 'beat', 'beat', 'beat'])
  })

  it('subdivides into eighths with soft off-beats, accents on quarters', () => {
    const g = metronomeGrid(4, 4, 1 / 8)
    expect(g.map((x) => x.level)).toEqual([
      'down', 'sub', 'beat', 'sub', 'beat', 'sub', 'beat', 'sub',
    ])
  })

  it('triplet eighths give two soft clicks between each beat', () => {
    const g = metronomeGrid(4, 4, 1 / 12)
    expect(g.length).toBe(12)
    expect(g.filter((x) => x.level !== 'sub').map((x) => x.level)).toEqual([
      'down', 'beat', 'beat', 'beat',
    ])
  })
})
