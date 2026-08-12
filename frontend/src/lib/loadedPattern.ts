/**
 * One-shot hand-off for loading a saved item into its generator. The account
 * page sets it and navigates; the target view consumes it once on mount.
 */
import type { Groove, Phrase } from '../types'

let pendingPhrase: Phrase | null = null
let pendingGroove: Groove | null = null

export function setPendingPhrase(phrase: Phrase): void {
  pendingPhrase = phrase
}

export function takePendingPhrase(): Phrase | null {
  const p = pendingPhrase
  pendingPhrase = null
  return p
}

export function setPendingGroove(groove: Groove): void {
  pendingGroove = groove
}

export function takePendingGroove(): Groove | null {
  const g = pendingGroove
  pendingGroove = null
  return g
}
