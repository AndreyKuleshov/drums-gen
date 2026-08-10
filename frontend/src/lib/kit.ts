/** Full-kit groove playback: one Tone.Player per voice, scheduled on the shared
 * transport. Velocity (accent / ghost) is applied via a per-voice gain at the
 * scheduled time. */
import * as Tone from 'tone'

import { parseFraction } from './audio'
import type { Groove, Hit, Surface } from '../types'

interface Voice {
  player: Tone.Player
  gain: Tone.Gain
}

let voices: Record<Surface, Voice> | null = null

function sampleUrl(name: string): string {
  return `${import.meta.env.BASE_URL}samples/${name}`
}

function makeVoice(file: string): Voice {
  const gain = new Tone.Gain(1).toDestination()
  const player = new Tone.Player(sampleUrl(file)).connect(gain)
  return { player, gain }
}

/** Create the players once and resolve when every sample buffer is loaded. */
async function ensureLoaded(): Promise<Record<Surface, Voice>> {
  if (voices === null) {
    voices = {
      kick: makeVoice('kick.wav'),
      snare: makeVoice('snare.wav'),
      hihat: makeVoice('hihat.wav'),
      hihat_open: makeVoice('hihat-open.wav'),
    }
  }
  await Tone.loaded()
  return voices
}

function velocity(hit: Hit): number {
  if (hit.surface === 'kick') return 1
  if (hit.surface === 'hihat' || hit.surface === 'hihat_open') return hit.accent ? 0.85 : 0.5
  return hit.ghost ? 0.3 : hit.accent ? 1 : 0.7
}

function barWholeNotes(num: number, den: number): number {
  return num / den
}

/** Unique hands-voice onsets per bar, flattened across the groove in play order.
 * The notation highlights the hands note at the same index. */
export function handsOnsetsWhole(groove: Groove): number[] {
  const out: number[] = []
  let elapsed = 0
  for (const bar of groove.bars) {
    const barLen = barWholeNotes(bar.time_sig.num, bar.time_sig.den)
    const uniq = [...new Set(bar.hands.map((h) => parseFraction(h.onset)))].sort((a, b) => a - b)
    for (const on of uniq) out.push(elapsed + on)
    elapsed += barLen
  }
  return out
}

export function grooveWholeNotes(groove: Groove): number {
  return groove.bars.reduce((s, b) => s + barWholeNotes(b.time_sig.num, b.time_sig.den), 0)
}

export interface GroovePlayOptions {
  onStep?: (index: number | null) => void
  onEnd?: () => void
  loop?: boolean
  tempoBpm?: number
}

export async function playGroove(groove: Groove, opts: GroovePlayOptions = {}): Promise<void> {
  await Tone.start()
  const kit = await ensureLoaded()
  const transport = Tone.getTransport()
  stopGroove()
  const draw = Tone.getDraw()

  const tempo = opts.tempoBpm ?? groove.tempo_bpm
  transport.bpm.value = tempo
  const wholeNoteSec = 240 / tempo

  // Schedule every hit across all bars.
  let elapsed = 0
  for (const bar of groove.bars) {
    const barLen = barWholeNotes(bar.time_sig.num, bar.time_sig.den)
    for (const hit of [...bar.hands, ...bar.feet]) {
      const timeSec = (elapsed + parseFraction(hit.onset)) * wholeNoteSec
      const voice = kit[hit.surface]
      const vel = velocity(hit)
      transport.schedule((time) => {
        try {
          voice.gain.gain.setValueAtTime(vel, time)
          voice.player.start(time)
        } catch {
          // benign retrigger at an identical instant; skip.
        }
      }, timeSec)
    }
    elapsed += barLen
  }

  // Highlight the hands voice (the hi-hat pulse) note-by-note.
  handsOnsetsWhole(groove).forEach((onWhole, index) => {
    transport.schedule((time) => {
      draw.schedule(() => opts.onStep?.(index), time)
    }, onWhole * wholeNoteSec)
  })

  const endSec = grooveWholeNotes(groove) * wholeNoteSec
  transport.loopStart = 0
  transport.loopEnd = endSec
  transport.loop = opts.loop ?? false
  transport.schedule((time) => {
    draw.schedule(() => {
      if (!transport.loop) {
        opts.onStep?.(null)
        opts.onEnd?.()
      }
    }, time)
  }, endSec)

  transport.start()
}

export function setGrooveTempo(bpm: number): void {
  Tone.getTransport().bpm.value = bpm
}

export function setGrooveLoop(enabled: boolean): void {
  Tone.getTransport().loop = enabled
}

export function stopGroove(): void {
  const transport = Tone.getTransport()
  transport.stop()
  transport.cancel(0)
  transport.loop = false
}
