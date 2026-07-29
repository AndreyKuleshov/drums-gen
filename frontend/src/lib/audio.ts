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

let synth: Tone.NoiseSynth | null = null

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

export async function playPhrase(phrase: Phrase): Promise<void> {
  await Tone.start()
  const transport = Tone.getTransport()
  stopPhrase()
  const s = getSynth()
  for (const event of scheduleTimes(phrase)) {
    transport.schedule((time) => {
      s.triggerAttackRelease('16n', time, event.velocity)
    }, event.timeSec)
  }
  transport.start()
}

export function stopPhrase(): void {
  const transport = Tone.getTransport()
  transport.stop()
  transport.cancel(0)
}
