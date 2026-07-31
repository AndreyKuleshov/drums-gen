/**
 * Backend base URL. Defaults to the same-origin `/api` prefix (Vite dev proxy in
 * development, nginx in prod). Override at build time with VITE_API_BASE only if
 * the backend lives on a separate domain.
 */
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? '/api'

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

/** Raised for a non-2xx response; carries the status and a human message. */
export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readError(resp: Response): Promise<string> {
  try {
    const body = (await resp.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const first = body.detail[0] as { msg?: unknown }
      if (typeof first.msg === 'string') return first.msg
    }
  } catch {
    // fall through to a generic message
  }
  return `Request failed (${resp.status})`
}

/**
 * JSON fetch wrapper that always sends the session cookie. Throws ApiError on a
 * non-2xx response; returns the parsed body (or undefined for 204).
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  // FormData sets its own multipart Content-Type (with boundary) — don't force JSON.
  const isForm = init.body instanceof FormData
  const baseHeaders: Record<string, string> = isForm ? {} : { 'Content-Type': 'application/json' }
  const resp = await fetch(apiUrl(path), {
    credentials: 'include',
    ...init,
    headers: { ...baseHeaders, ...(init.headers ?? {}) },
  })
  if (!resp.ok) throw new ApiError(resp.status, await readError(resp))
  if (resp.status === 204) return undefined as T
  return (await resp.json()) as T
}
