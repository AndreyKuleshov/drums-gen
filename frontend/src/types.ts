export interface Stroke {
  duration: string
  hand: 'L' | 'R'
  accent: boolean
  articulation: string
  surface: string
}

export interface Bar {
  time_sig: { num: number; den: number }
  strokes: Stroke[]
}

export interface Phrase {
  time_sig: { num: number; den: number }
  tempo_bpm: number
  subdivision: string
  accent_mode: string
  bars: Bar[]
}
