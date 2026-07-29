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

export function scheduleTimes(phrase: Phrase): ScheduledStroke[] {
  const wholeNoteSec = 240 / phrase.tempo_bpm // 4 quarters * (60/bpm)
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
export function metronomeTimes(phrase: Phrase): { timeSec: number; down: boolean }[] {
  const wholeNoteSec = 240 / phrase.tempo_bpm
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

let synth: Tone.NoiseSynth | null = null
let click: Tone.MembraneSynth | null = null

function getSynth(): Tone.NoiseSynth {
  if (synth === null) {
    synth = new Tone.NoiseSynth({
      noise: { type: 'white' },
      envelope: { attack: 0.001, decay: 0.08, sustain: 0 },
    })
    const filter = new Tone.Filter(3000, 'bandpass').toDestination()
    synth.connect(filter)
  }
  return synth
}

function getClick(): Tone.MembraneSynth {
  if (click === null) {
    click = new Tone.MembraneSynth({
      pitchDecay: 0.008,
      octaves: 2,
      envelope: { attack: 0.001, decay: 0.05, sustain: 0 },
    }).toDestination()
    click.volume.value = -6
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
}

export async function playPhrase(phrase: Phrase, opts: PlayOptions = {}): Promise<void> {
  await Tone.start()
  const transport = Tone.getTransport()
  stopPhrase()
  const draw = Tone.getDraw()
  const s = getSynth()

  scheduleTimes(phrase).forEach((event, index) => {
    transport.schedule((time) => {
      s.triggerAttackRelease('16n', time, event.velocity)
      draw.schedule(() => opts.onStep?.(index), time)
    }, event.timeSec)
  })

  if (opts.metronome) {
    const c = getClick()
    for (const beat of metronomeTimes(phrase)) {
      transport.schedule((time) => {
        c.triggerAttackRelease(beat.down ? 'C3' : 'G2', '32n', time, beat.down ? 1 : 0.5)
      }, beat.timeSec)
    }
  }

  const endSec = phraseWholeNotes(phrase) * (240 / phrase.tempo_bpm)
  transport.schedule((time) => {
    draw.schedule(() => {
      opts.onStep?.(null)
      opts.onEnd?.()
    }, time)
  }, endSec)

  transport.start()
}

export function stopPhrase(): void {
  const transport = Tone.getTransport()
  transport.stop()
  transport.cancel(0)
}
