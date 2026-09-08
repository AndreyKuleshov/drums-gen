import { reactive } from 'vue'

/**
 * Shared sample-load progress, so the transport can show one "Loading samples…"
 * modal with a real progress bar. `total` is how many buffers a fresh load is
 * fetching, `loaded` counts up as each decodes, and `active` is true only while
 * a load is in flight — cached plays never flip it, so the modal doesn't flash.
 */
export const sampleLoad = reactive({ active: false, loaded: 0, total: 0 })

/** Start tracking a load of `total` buffers. */
export function beginSampleLoad(total: number): void {
  sampleLoad.active = true
  sampleLoad.loaded = 0
  sampleLoad.total = total
}

/** Mark one buffer decoded; clears `active` when the last one lands. */
export function markSampleLoaded(): void {
  sampleLoad.loaded = Math.min(sampleLoad.total, sampleLoad.loaded + 1)
  if (sampleLoad.loaded >= sampleLoad.total) sampleLoad.active = false
}
