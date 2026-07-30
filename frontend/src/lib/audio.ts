import * as Tone from 'tone'

import type { Phrase } from '../types'

export function parseFraction(s: string): number {
  const [num, den] = s.split('/').map(Number)
  return num / den
}

export interface ScheduledStroke {
  timeSec: number
  velocity: number
  hand: 'L' | 'R'
}

export function scheduleTimes(phrase: Phrase, tempoBpm: number = phrase.tempo_bpm): ScheduledStroke[] {
  const wholeNoteSec = 240 / tempoBpm // 4 quarters * (60/bpm)
  const events: ScheduledStroke[] = []
  let elapsedWhole = 0
  for (const bar of phrase.bars) {
    for (const stroke of bar.strokes) {
      events.push({
        timeSec: elapsedWhole * wholeNoteSec,
        velocity: stroke.accent ? 1.0 : 0.6,
        hand: stroke.hand,
      })
      elapsedWhole += parseFraction(stroke.duration)
    }
  }
  return events
}

/** Whole-note count spanned by the phrase. */
export function phraseWholeNotes(phrase: Phrase): number {
  return phrase.bars
    .flatMap((b) => b.strokes)
    .reduce((sum, s) => sum + parseFraction(s.duration), 0)
}

/** Beat length in whole notes (compound meters group in threes). */
function beatWholeNotes(num: number, den: number): number {
  const compound = (den === 8 || den === 16) && num % 3 === 0 && num > 3
  return (compound ? 3 : 1) / den
}

/** Absolute times (sec) of every metronome beat, flagged as downbeat or not. */
export function metronomeTimes(
  phrase: Phrase,
  tempoBpm: number = phrase.tempo_bpm,
): { timeSec: number; down: boolean }[] {
  const wholeNoteSec = 240 / tempoBpm
  const { num, den } = phrase.time_sig
  const barWhole = num / den
  const beat = beatWholeNotes(num, den)
  const out: { timeSec: number; down: boolean }[] = []
  for (let bar = 0; bar < phrase.bars.length; bar++) {
    for (let t = 0; t + 1e-9 < barWhole; t += beat) {
      out.push({ timeSec: (bar * barWhole + t) * wholeNoteSec, down: t < 1e-9 })
    }
  }
  return out
}

// Snare voice: two clearly audible levels — a normal hit and a louder, fuller
// accent (extra brightness + a bit of drum body). Both are plainly heard; the
// accent just stands out. (Swap these for real samples later via a Tone.Sampler.)
let accentNoise: Tone.NoiseSynth | null = null
let normalNoise: Tone.NoiseSynth | null = null
let body: Tone.MembraneSynth | null = null
let click: Tone.MembraneSynth | null = null

function getAccentNoise(): Tone.NoiseSynth {
  if (accentNoise === null) {
    accentNoise = new Tone.NoiseSynth({
      noise: { type: 'white' },
      envelope: { attack: 0.001, decay: 0.15, sustain: 0 },
    })
    const filter = new Tone.Filter(4200, 'bandpass').toDestination()
    filter.Q.value = 0.6
    accentNoise.connect(filter)
    accentNoise.volume.value = 1
  }
  return accentNoise
}

function getNormalNoise(): Tone.NoiseSynth {
  if (normalNoise === null) {
    normalNoise = new Tone.NoiseSynth({
      noise: { type: 'white' },
      envelope: { attack: 0.001, decay: 0.08, sustain: 0 },
    })
    const filter = new Tone.Filter(2700, 'bandpass').toDestination()
    filter.Q.value = 0.6
    normalNoise.connect(filter)
    normalNoise.volume.value = -5
  }
  return normalNoise
}

function getBody(): Tone.MembraneSynth {
  if (body === null) {
    body = new Tone.MembraneSynth({
      pitchDecay: 0.03,
      octaves: 3,
      envelope: { attack: 0.001, decay: 0.12, sustain: 0 },
    }).toDestination()
    body.volume.value = -7
  }
  return body
}

function hit(time: number, accent: boolean): void {
  if (accent) {
    getAccentNoise().triggerAttackRelease('16n', time, 1)
    getBody().triggerAttackRelease('D2', '16n', time, 0.9)
  } else {
    getNormalNoise().triggerAttackRelease('16n', time, 0.85)
  }
}

function getClick(): Tone.MembraneSynth {
  if (click === null) {
    click = new Tone.MembraneSynth({
      pitchDecay: 0.006,
      octaves: 4,
      envelope: { attack: 0.001, decay: 0.04, sustain: 0 },
    }).toDestination()
    click.volume.value = -4
  }
  return click
}

export interface PlayOptions {
  /** Called (draw-synced) as each note sounds; receives the global note index, or null at the end. */
  onStep?: (index: number | null) => void
  /** Called when playback finishes. */
  onEnd?: () => void
  /** Play a metronome click track alongside the pattern. */
  metronome?: boolean
  /** Repeat the pattern continuously until stopped. */
  loop?: boolean
  /** Playback tempo; overrides the phrase's baked-in tempo so it can change live. */
  tempoBpm?: number
}

export async function playPhrase(phrase: Phrase, opts: PlayOptions = {}): Promise<void> {
  await Tone.start()
  const transport = Tone.getTransport()
  stopPhrase()
  const draw = Tone.getDraw()
  const tempo = opts.tempoBpm ?? phrase.tempo_bpm

  scheduleTimes(phrase, tempo).forEach((event, index) => {
    transport.schedule((time) => {
      hit(time, event.velocity >= 1)
      draw.schedule(() => opts.onStep?.(index), time)
    }, event.timeSec)
  })

  if (opts.metronome) {
    const c = getClick()
    for (const beat of metronomeTimes(phrase, tempo)) {
      transport.schedule((time) => {
        c.triggerAttackRelease(beat.down ? 'C3' : 'G2', '32n', time, beat.down ? 1 : 0.5)
      }, beat.timeSec)
    }
  }

  const endSec = phraseWholeNotes(phrase) * (240 / tempo)
  if (opts.loop) {
    // Repeat forever: the scheduled notes and their draw callbacks re-fire each
    // cycle, so highlighting loops too. No terminal onEnd — Stop ends it.
    transport.loop = true
    transport.loopStart = 0
    transport.loopEnd = endSec
  } else {
    transport.schedule((time) => {
      draw.schedule(() => {
        opts.onStep?.(null)
        opts.onEnd?.()
      }, time)
    }, endSec)
  }

  transport.start()
}

export function stopPhrase(): void {
  const transport = Tone.getTransport()
  transport.stop()
  transport.cancel(0)
  transport.loop = false
}

/** Loop a metronome click track on its own (no pattern), one bar of the given meter. */
export async function playMetronome(opts: {
  tempoBpm: number
  num: number
  den: number
}): Promise<void> {
  await Tone.start()
  const transport = Tone.getTransport()
  stopPhrase()
  const c = getClick()
  const wholeNoteSec = 240 / opts.tempoBpm
  const barWhole = opts.num / opts.den
  const beat = beatWholeNotes(opts.num, opts.den)
  for (let t = 0; t + 1e-9 < barWhole; t += beat) {
    const down = t < 1e-9
    transport.schedule((time) => {
      c.triggerAttackRelease(down ? 'C3' : 'G2', '32n', time, down ? 1 : 0.5)
    }, t * wholeNoteSec)
  }
  transport.loop = true
  transport.loopStart = 0
  transport.loopEnd = barWhole * wholeNoteSec
  transport.start()
}
