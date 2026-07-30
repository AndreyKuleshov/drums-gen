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

/** Absolute times (sec) + accent level of every metronome click across the phrase. */
export function metronomeTimes(
  phrase: Phrase,
  tempoBpm: number = phrase.tempo_bpm,
  subWhole?: number,
): { timeSec: number; level: 'down' | 'beat' | 'sub' }[] {
  const wholeNoteSec = 240 / tempoBpm
  const { num, den } = phrase.time_sig
  const barWhole = num / den
  const grid = metronomeGrid(num, den, subWhole)
  const out: { timeSec: number; level: 'down' | 'beat' | 'sub' }[] = []
  for (let bar = 0; bar < phrase.bars.length; bar++) {
    for (const g of grid) {
      out.push({ timeSec: (bar * barWhole + g.offsetWhole) * wholeNoteSec, level: g.level })
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
let click: Tone.PolySynth<Tone.Synth> | null = null

/** Trigger a voice, ignoring Tone's "start time must be strictly greater"
 * error that a monophonic voice throws if the transport re-fires an event at
 * the same instant (e.g. on a live tempo change during a loop). */
function safeTrigger(fn: () => void): void {
  try {
    fn()
  } catch {
    // benign double-trigger at an identical time; skip this hit.
  }
}

// Metronome beep levels (Hz): bar downbeat highest, quarter beats accented,
// in-between subdivisions soft.
type ClickLevel = 'down' | 'beat' | 'sub'
const CLICK_HZ: Record<ClickLevel, number> = { down: 2000, beat: 1400, sub: 950 }
const CLICK_VEL: Record<ClickLevel, number> = { down: 1, beat: 0.7, sub: 0.32 }

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
  safeTrigger(() => {
    if (accent) {
      getAccentNoise().triggerAttackRelease('16n', time, 1)
      getBody().triggerAttackRelease('D2', '16n', time, 0.9)
    } else {
      getNormalNoise().triggerAttackRelease('16n', time, 0.85)
    }
  })
}

let clickVolumeDb = -10

function getClick(): Tone.PolySynth<Tone.Synth> {
  if (click === null) {
    click = new Tone.PolySynth(Tone.Synth).toDestination()
    click.set({
      oscillator: { type: 'square' },
      envelope: { attack: 0.0005, decay: 0.03, sustain: 0, release: 0.01 },
    })
    click.volume.value = clickVolumeDb
  }
  return click
}

/** Set metronome loudness live (level 0..1). Applies to standalone and overlay.
 * Curve centred so mid-slider (0.5) is 0 dB with headroom above (up to +12 dB). */
export function setMetronomeVolume(level: number): void {
  clickVolumeDb = level <= 0.001 ? -Infinity : 24 * level - 12
  if (click !== null) click.volume.value = clickVolumeDb
}

// The pattern-overlay click is always scheduled but gated by this live flag, so
// the "Click" toggle can turn it on/off during playback without restarting.
let overlayClickOn = false

/** Toggle the pattern-overlay metronome click live (no restart). */
export function setOverlayClick(on: boolean): void {
  overlayClickOn = on
}

function tick(time: number, level: ClickLevel): void {
  safeTrigger(() =>
    getClick().triggerAttackRelease(CLICK_HZ[level], '64n', time, CLICK_VEL[level]),
  )
}

/** Click positions and accent levels for one meter, at a given click subdivision.
 * `subWhole` is the click spacing in whole notes; omit for one click per beat. */
export function metronomeGrid(
  num: number,
  den: number,
  subWhole?: number,
): { offsetWhole: number; level: ClickLevel }[] {
  const barWhole = num / den
  const beat = beatWholeNotes(num, den)
  const step = subWhole ?? beat
  const stepsPerBar = Math.round(barWhole / step)
  const beatSteps = Math.max(1, Math.round(beat / step))
  const out: { offsetWhole: number; level: ClickLevel }[] = []
  for (let i = 0; i < stepsPerBar; i++) {
    const level: ClickLevel = i === 0 ? 'down' : i % beatSteps === 0 ? 'beat' : 'sub'
    out.push({ offsetWhole: i * step, level })
  }
  return out
}

export interface PlayOptions {
  /** Called (draw-synced) as each note sounds; receives the global note index, or null at the end. */
  onStep?: (index: number | null) => void
  /** Called when playback finishes. */
  onEnd?: () => void
  /** Play a metronome click track alongside the pattern. */
  metronome?: boolean
  /** Metronome click spacing (whole notes); omit for one click per beat. */
  metroSubWhole?: number
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

  // Events are scheduled in seconds computed at `tempo`, and the transport's bpm
  // is set to the same value. The transport stores events by tick, so those
  // ticks land on the musical positions — and changing bpm later (setTempo)
  // retimes everything live, without restarting.
  transport.bpm.value = tempo

  scheduleTimes(phrase, tempo).forEach((event, index) => {
    transport.schedule((time) => {
      hit(time, event.velocity >= 1)
      draw.schedule(() => opts.onStep?.(index), time)
    }, event.timeSec)
  })

  // Always schedule the overlay clicks; the live flag decides whether they sound.
  overlayClickOn = opts.metronome ?? false
  for (const beat of metronomeTimes(phrase, tempo, opts.metroSubWhole)) {
    transport.schedule((time) => {
      if (overlayClickOn) tick(time, beat.level)
    }, beat.timeSec)
  }

  // Always set the loop bounds so Loop can be toggled live mid-playback; whether
  // it actually loops is just the transport.loop flag.
  const endSec = phraseWholeNotes(phrase) * (240 / tempo)
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

/** Change playback tempo live (no restart). */
export function setTempo(bpm: number): void {
  Tone.getTransport().bpm.value = bpm
}

/** Toggle looping of the currently-playing pattern live. */
export function setLoop(enabled: boolean): void {
  Tone.getTransport().loop = enabled
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
  subWhole?: number
}): Promise<void> {
  await Tone.start()
  const transport = Tone.getTransport()
  stopPhrase()
  transport.bpm.value = opts.tempoBpm
  const wholeNoteSec = 240 / opts.tempoBpm
  const barWhole = opts.num / opts.den
  for (const g of metronomeGrid(opts.num, opts.den, opts.subWhole)) {
    transport.schedule((time) => tick(time, g.level), g.offsetWhole * wholeNoteSec)
  }
  transport.loop = true
  transport.loopStart = 0
  transport.loopEnd = barWhole * wholeNoteSec
  transport.start()
}
