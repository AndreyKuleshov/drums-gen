// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

// `page`/`moderate` must be declared inside `vi.hoisted` (not as plain top-level
// `const`s): the mocked module is a dependency of `AdminRatingsView.vue`, so ESM
// evaluates its `vi.mock` factory before this test file's own top-level code runs.
// A plain `const page = {...}` below the factory would still be in its temporal
// dead zone when the factory dereferences it eagerly via `.mockResolvedValue(page)`.
const { page, moderate } = vi.hoisted(() => {
  const page = {
    items: [
      { id: 'r1', rating: -1, tags: ['too_busy'], note: null, kind: 'exercise', pattern: {}, params: { voicing: 'snare', subdivision: '1/16', tempo_bpm: 120, num_bars: 1 }, generator_version: '2026-09-15', seed: null, rater_email: 'a@b.c', created_at: new Date().toISOString(), moderated_out: false },
    ],
    total: 1,
    summary: { total: 1, likes: 0, dislikes: 1, top_dislike_tags: [{ tag: 'too_busy', count: 1 }] },
  }
  const moderate = vi.fn().mockResolvedValue({ ...page.items[0], moderated_out: true })
  return { page, moderate }
})
vi.mock('../lib/ratings', () => ({
  adminListRatings: vi.fn().mockResolvedValue(page),
  adminModerate: (...a: unknown[]) => moderate(...a),
}))

import AdminRatingsView from './AdminRatingsView.vue'

describe('AdminRatingsView', () => {
  it('renders the summary + table and moderates a row', async () => {
    const wrapper = mount(AdminRatingsView, {
      global: { stubs: { RouterLink: true, AuthNav: true, RatingPreviewModal: true } },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('too_busy')
    expect(wrapper.find('.ratetable').exists()).toBe(true)
    await wrapper.find('.ratebtn--danger').trigger('click')
    expect(moderate).toHaveBeenCalledWith('r1', true)
  })
})
