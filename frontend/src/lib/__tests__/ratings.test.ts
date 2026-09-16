import { describe, expect, it, vi } from 'vitest'

vi.mock('../api', () => ({
  apiFetch: vi.fn().mockResolvedValue({ id: 'x', rating: 1, tags: [], note: null, created_at: 'now' }),
}))

import { apiFetch } from '../api'
import { ratePattern } from '../ratings'

describe('ratePattern', () => {
  it('POSTs the rating to /patterns2/rate', async () => {
    await ratePattern({
      rating: 1, tags: ['groovy'], note: null, kind: 'exercise',
      pattern: { a: 1 }, params: { b: 2 }, seed: null,
    })
    expect(apiFetch).toHaveBeenCalledWith('/patterns2/rate', expect.objectContaining({ method: 'POST' }))
    const call = (apiFetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    const body = JSON.parse(call[1].body as string)
    expect(body.rating).toBe(1)
    expect(body.tags).toEqual(['groovy'])
  })
})
