/** API calls for liked patterns and profile edits. */
import { apiFetch } from './api'
import type { Phrase, User } from '../types'

export interface LikedPattern {
  id: string
  title: string | null
  phrase: Phrase
  meta: Record<string, unknown>
  created_at: string
}

export function likePattern(
  phrase: Phrase,
  meta: Record<string, unknown>,
  title?: string,
): Promise<LikedPattern> {
  return apiFetch<LikedPattern>('/patterns/like', {
    method: 'POST',
    body: JSON.stringify({ phrase, meta, title: title ?? null }),
  })
}

export function listLiked(): Promise<LikedPattern[]> {
  return apiFetch<LikedPattern[]>('/patterns/liked')
}

export function unlikePattern(id: string): Promise<void> {
  return apiFetch(`/patterns/liked/${id}`, { method: 'DELETE' })
}

export function updateProfile(displayName: string, bio: string): Promise<User> {
  return apiFetch<User>('/account', {
    method: 'PATCH',
    body: JSON.stringify({ display_name: displayName, bio }),
  })
}

export async function uploadAvatar(file: File): Promise<User> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch<User>('/account/avatar', { method: 'POST', body: form })
}
