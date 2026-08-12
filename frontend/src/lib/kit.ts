/** Full-kit groove playback: one Tone.Player per voice, scheduled on the shared
 * transport. Velocity (accent / ghost) is applied via a per-voice gain at the
 * scheduled time. */
import * as Tone from 'tone'

import { parseFraction, scheduleMetro, setOverlayClick } from './audio'
import type { Groove, Hit, Surface } from '../types'

interface Voice {
  player: Tone.Player
  gain: Tone.Gain
}

let voices: Record<Surface, Voice> | null = null

// Bump this when the sample files change so browsers don't serve a stale cached
// .wav (JS reloads on deploy, but the audio files are cached aggressively).
const SAMPLE_VERSION = '3'
function sampleUrl(name: string): string {
  return `${import.meta.env.BASE_URL}samples/${name}?v=${SAMPLE_VERSION}`
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
      tom_high: makeVoice('tom-high.wav'),
      tom_mid: makeVoice('tom-mid.wav'),
      tom_low: makeVoice('tom-low.wav'),
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

/** Unique onsets across BOTH voices (hands + feet) per bar, flattened across the
 * groove in play order. Each is one highlight "step"; the notation lights up every
 * note (hands + feet) sharing that onset, so simultaneous hits highlight together. */
export function combinedOnsetsWhole(groove: Groove): number[] {
  const out: number[] = []
  let elapsed = 0
  for (const bar of groove.bars) {
    const barLen = barWholeNotes(bar.time_sig.num, bar.time_sig.den)
    const uniq = [
      ...new Set([...bar.hands, ...bar.feet].map((h) => parseFraction(h.onset))),
    ].sort((a, b) => a - b)
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
  /** Play a metronome overlay click alongside the groove (shared click settings). */
  metronome?: boolean
  /** Count-in bars of metronome before the groove starts (0 = none). Plays once. */
  prerollBars?: number
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

  // Count-in + live overlay click share the transport with the kit hits. The
  // returned offset shifts every note past the count-in so it plays once even
  // when looping.
  const prerollSec = scheduleMetro({
    bars: groove.bars.map((b) => ({ num: b.time_sig.num, den: b.time_sig.den })),
    wholeNoteSec,
    prerollBars: opts.prerollBars,
    overlay: opts.metronome ?? false,
  })

  // Schedule every hit across all bars.
  let elapsed = 0
  for (const bar of groove.bars) {
    const barLen = barWholeNotes(bar.time_sig.num, bar.time_sig.den)
    for (const hit of [...bar.hands, ...bar.feet]) {
      const timeSec = prerollSec + (elapsed + parseFraction(hit.onset)) * wholeNoteSec
      const voice = kit[hit.surface]
      const vel = velocity(hit)
      // Flam (1) / drag (2): soft quick grace hits just before the main note.
      const graces = hit.articulation === 'drag' ? 2 : hit.articulation === 'flam' ? 1 : 0
      for (let k = 0; k < graces; k++) {
        const graceTime = Math.max(0, timeSec - (graces - k) * 0.035)
        transport.schedule((time) => {
          try {
            voice.gain.gain.setValueAtTime(0.32, time)
            voice.player.start(time)
          } catch {
            // benign retrigger; skip.
          }
        }, graceTime)
      }
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

  // Highlight every voice note-by-note (all notes sharing an onset light together).
  combinedOnsetsWhole(groove).forEach((onWhole, index) => {
    transport.schedule((time) => {
      draw.schedule(() => opts.onStep?.(index), time)
    }, prerollSec + onWhole * wholeNoteSec)
  })

  const endSec = prerollSec + grooveWholeNotes(groove) * wholeNoteSec
  transport.loopStart = prerollSec
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

/** Toggle the groove-overlay metronome click live (no restart). */
export function setGrooveMetronome(on: boolean): void {
  setOverlayClick(on)
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
