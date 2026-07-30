import { ref, type Ref } from 'vue'

// MVP settings persistence in localStorage. Values are LOADED on init but only
// WRITTEN when the user commits by pressing Generate (flushSettings()). Replace
// with server-side storage once auth exists.
const PREFIX = 'drumgen:'
const savers: Array<() => void> = []

export function loadSetting<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw === null ? fallback : (JSON.parse(raw) as T)
  } catch {
    return fallback
  }
}

export function saveSetting(key: string, value: unknown): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    // storage unavailable / quota — settings just won't persist this session.
  }
}

/** Register a save callback run by flushSettings() (on Generate). */
export function registerPersist(save: () => void): void {
  savers.push(save)
}

/** Write every registered setting to localStorage. Call on the Generate action. */
export function flushSettings(): void {
  for (const save of savers) save()
}

/** A ref that loads its initial value from localStorage and is written on flush. */
export function persistedRef<T>(key: string, fallback: T): Ref<T> {
  const r = ref(loadSetting(key, fallback)) as Ref<T>
  registerPersist(() => saveSetting(key, r.value))
  return r
}
