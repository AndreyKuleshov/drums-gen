import { describe, expect, it } from 'vitest'

import type { Bar } from '../../types'
import type { NoteSpec } from '../score'
import { barToNoteSpecs, beamGroups, isTripletDuration, vexDuration } from '../score'

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

describe('isTripletDuration', () => {
  it('identifies triplet-based subdivisions', () => {
    expect(isTripletDuration('1/12')).toBe(true)
    expect(isTripletDuration('1/16')).toBe(false)
  })
})

describe('barToNoteSpecs', () => {
  it('produces one spec per stroke', () => {
    const bar: Bar = {
      time_sig: { num: 1, den: 4 },
      strokes: [
        {
          duration: '1/4',
          hand: 'R',
          accent: true,
          articulation: 'normal',
          surface: 'snare',
          grace: 0,
          group: 0,
        },
      ],
    }
    expect(barToNoteSpecs(bar)).toEqual([
      { duration: 'q', accent: true, sticking: 'R', grace: 0, group: 0 },
    ])
  })
})

describe('beamGroups', () => {
  const spec = (duration: string, group: number): NoteSpec => ({
    duration,
    accent: false,
    sticking: 'R',
    grace: 0,
    group,
  })

  it('beams consecutive beamable notes sharing a group', () => {
    // group 0: 4 sixteenths (one paradiddle), group 1: 2 sixteenths (one double)
    const specs = [
      spec('16', 0),
      spec('16', 0),
      spec('16', 0),
      spec('16', 0),
      spec('16', 1),
      spec('16', 1),
    ]
    expect(beamGroups(specs)).toEqual([
      [0, 1, 2, 3],
      [4, 5],
    ])
  })

  it('does not beam across group boundaries and drops singletons', () => {
    // group 0 has a single note -> not beamed; group 1 has two -> beamed
    const specs = [spec('16', 0), spec('16', 1), spec('16', 1)]
    expect(beamGroups(specs)).toEqual([[1, 2]])
  })

  it('excludes non-beamable (quarter and longer) durations', () => {
    const specs = [spec('q', 0), spec('q', 0)]
    expect(beamGroups(specs)).toEqual([])
  })
})
