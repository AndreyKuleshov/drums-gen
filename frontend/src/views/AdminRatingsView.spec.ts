// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const { list, moderate } = vi.hoisted(() => ({ list: vi.fn(), moderate: vi.fn() }))
vi.mock('../lib/ratings', () => ({ adminListRatings: list, adminModerate: moderate }))

import AdminRatingsView from './AdminRatingsView.vue'

const row = {
  id: 'r1', rating: -1, tags: ['too_busy'], note: null, kind: 'exercise', pattern: {},
  params: { voicing: 'snare', subdivision: '1/16', tempo_bpm: 120, num_bars: 1 },
  generator_version: '2026-09-15', seed: null, rater_email: 'a@b.c',
  created_at: new Date().toISOString(), moderated_out: false,
}
const page = { items: [row], total: 1, summary: { total: 1, likes: 0, dislikes: 1, top_dislike_tags: [{ tag: 'too_busy', count: 1 }] } }

const opts = { global: { stubs: { RatingPreviewModal: true } } }

describe('AdminRatingsView', () => {
  it('renders the table and confirms before removing', async () => {
    list.mockResolvedValue(page)
    moderate.mockResolvedValue({ ...row, moderated_out: true })
    const wrapper = mount(AdminRatingsView, opts)
    await flushPromises()
    expect(wrapper.text()).toContain('too_busy')
    await wrapper.find('.ratebtn--danger').trigger('click') // Remove → confirm state
    expect(moderate).not.toHaveBeenCalled()
    await wrapper.find('.ratebtn--confirm').trigger('click') // Confirm
    expect(moderate).toHaveBeenCalledWith('r1', true)
  })

  it('re-fetches when the rating filter changes', async () => {
    list.mockResolvedValue(page)
    const wrapper = mount(AdminRatingsView, opts)
    await flushPromises()
    list.mockClear()
    await wrapper.find('[data-test="rating-filter"]').setValue('1')
    await flushPromises()
    expect(list).toHaveBeenCalledWith(expect.objectContaining({ rating: 1 }))
  })
})
