/** API calls for rating generated patterns + admin review/moderation. */
import { apiFetch } from './api'

export type RatingTag =
  | 'too_busy' | 'boring' | 'unmusical' | 'awkward_sticking' | 'repetitive' | 'too_hard'
  | 'groovy' | 'creative' | 'playable'

export interface RateInput {
  rating: -1 | 0 | 1
  tags: RatingTag[]
  note: string | null
  kind: 'exercise' | 'pattern'
  pattern: unknown
  params: Record<string, unknown>
  seed: number | null
}

export interface RatingOut {
  id: string
  rating: number
  tags: string[]
  note: string | null
  created_at: string
}

/** Upsert a rating; `rating: 0` removes it (server replies 204 → undefined). */
export function ratePattern(input: RateInput): Promise<RatingOut | undefined> {
  return apiFetch<RatingOut | undefined>('/patterns2/rate', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export interface AdminRating {
  id: string
  rating: number
  tags: string[]
  note: string | null
  kind: 'exercise' | 'pattern'
  pattern: unknown
  params: Record<string, unknown>
  generator_version: string
  seed: number | null
  rater_email: string
  created_at: string
  moderated_out: boolean
}

export interface TagCount {
  tag: string
  count: number
}

export interface RatingSummary {
  total: number
  likes: number
  dislikes: number
  top_dislike_tags: TagCount[]
}

export interface AdminRatingsPage {
  items: AdminRating[]
  total: number
  summary: RatingSummary
}

export function adminListRatings(
  params: { limit?: number; offset?: number; rating?: number; tag?: string; includeModerated?: boolean } = {},
): Promise<AdminRatingsPage> {
  const q = new URLSearchParams()
  if (params.limit != null) q.set('limit', String(params.limit))
  if (params.offset != null) q.set('offset', String(params.offset))
  if (params.rating != null) q.set('rating', String(params.rating))
  if (params.tag) q.set('tag', params.tag)
  if (params.includeModerated) q.set('include_moderated', 'true')
  const qs = q.toString()
  return apiFetch<AdminRatingsPage>(`/admin/ratings${qs ? `?${qs}` : ''}`)
}

export function adminModerate(id: string, moderatedOut: boolean): Promise<AdminRating> {
  return apiFetch<AdminRating>(`/admin/ratings/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ moderated_out: moderatedOut }),
  })
}
