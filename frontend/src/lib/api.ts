/** Backend base URL. Override at build/dev time with VITE_API_BASE. */
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}
