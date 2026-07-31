/**
 * A one-shot hand-off for loading a saved pattern into the generator. The
 * account page sets it, then navigates to `/`; the generator consumes it once
 * on mount and clears it.
 */
import type { Phrase } from '../types'

let pending: Phrase | null = null

export function setPendingPhrase(phrase: Phrase): void {
  pending = phrase
}

export function takePendingPhrase(): Phrase | null {
  const p = pending
  pending = null
  return p
}
