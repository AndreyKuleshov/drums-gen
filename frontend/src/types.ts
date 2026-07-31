export interface User {
  id: string
  email: string
  display_name: string
  bio: string
  avatar_url: string | null
  is_verified: boolean
}

export interface Stroke {
  duration: string
  hand: 'L' | 'R'
  accent: boolean
  articulation: string
  surface: string
  /** Grace notes ornamenting this stroke: 0 = none, 1 = flam, 2 = drag. */
  grace: number
  /** Index of the rudiment instance this stroke belongs to; notes are beamed by group. */
  group: number
}

export interface Bar {
  time_sig: { num: number; den: number }
  strokes: Stroke[]
}

export interface Rudiment {
  id: string
  name: string
  difficulty: 'beginner' | 'mid' | 'pro'
  length: number
  filler: boolean
  sticking: ('L' | 'R')[]
  accents: boolean[]
  grace: number[]
}

export interface PatternConfig {
  meter: string
  grid: string
  feel: string
  accents: string
  bars: number
  difficulty: string
}

export interface Phrase {
  time_sig: { num: number; den: number }
  tempo_bpm: number
  subdivision: string
  accent_mode: string
  bars: Bar[]
}
