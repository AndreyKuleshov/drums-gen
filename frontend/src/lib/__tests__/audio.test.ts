import { describe, expect, it } from 'vitest'

import type { Phrase } from '../../types'
import { clickLevelAt, parseFraction, scheduleTimes } from '../audio'

const phrase: Phrase = {
  time_sig: { num: 2, den: 4 },
  tempo_bpm: 60,
  subdivision: '1/4',
  accent_mode: 'rudiment',
  bars: [
    {
      time_sig: { num: 2, den: 4 },
      strokes: [
        { duration: '1/4', hand: 'R', accent: true, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
        { duration: '1/4', hand: 'L', accent: false, articulation: 'normal', surface: 'snare', grace: 0, group: 1 },
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

describe('clickLevelAt', () => {
  const beat = 1 / 4 // quarter-note beat in 4/4

  it('quarter subdivision: click only on beats, downbeat at bar start', () => {
    expect(clickLevelAt(0, beat, 1 / 4)).toBe('down')
    expect(clickLevelAt(1 / 4, beat, 1 / 4)).toBe('beat')
    expect(clickLevelAt(1 / 8, beat, 1 / 4)).toBeNull()
  })

  it('eighth subdivision: soft off-beats between accented beats', () => {
    expect(clickLevelAt(0, beat, 1 / 8)).toBe('down')
    expect(clickLevelAt(1 / 8, beat, 1 / 8)).toBe('sub')
    expect(clickLevelAt(1 / 4, beat, 1 / 8)).toBe('beat')
  })

  it('triplet subdivision: two soft clicks between beats, no straight-16th click', () => {
    expect(clickLevelAt(1 / 12, beat, 1 / 12)).toBe('sub')
    expect(clickLevelAt(1 / 4, beat, 1 / 12)).toBe('beat')
    expect(clickLevelAt(1 / 16, beat, 1 / 12)).toBeNull()
  })
})
