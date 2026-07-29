import { describe, expect, it } from 'vitest'

import type { Bar } from '../../types'
import { barToNoteSpecs, vexDuration } from '../score'

describe('vexDuration', () => {
  it('maps common durations', () => {
    expect(vexDuration('1/4')).toBe('q')
    expect(vexDuration('1/8')).toBe('8')
    expect(vexDuration('1/16')).toBe('16')
    expect(vexDuration('1/12')).toBe('8')
  })

  it('throws on unsupported', () => {
    expect(() => vexDuration('1/7')).toThrow()
  })
})

describe('barToNoteSpecs', () => {
  it('produces one spec per stroke', () => {
    const bar: Bar = {
      time_sig: { num: 1, den: 4 },
      strokes: [
        { duration: '1/4', hand: 'R', accent: true, articulation: 'normal', surface: 'snare' },
      ],
    }
    expect(barToNoteSpecs(bar)).toEqual([{ duration: 'q', accent: true, sticking: 'R' }])
  })
})
