// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../lib/auth', () => ({ useAuth: () => ({ isAuthenticated: { value: true } }) }))
const rate = vi.fn().mockResolvedValue(undefined)
vi.mock('../lib/ratings', () => ({ ratePattern: (...a: unknown[]) => rate(...a) }))
const like = vi.fn().mockResolvedValue({ id: 'fav1' })
const unlike = vi.fn().mockResolvedValue(undefined)
vi.mock('../lib/patterns', () => ({
  likePattern: (...a: unknown[]) => like(...a),
  unlikePattern: (...a: unknown[]) => unlike(...a),
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

import RateControl from './RateControl.vue'

const props = { pattern: { a: 1 }, kind: 'exercise' as const, params: {}, seed: null, meta: { kind: 'exercise' } }

describe('RateControl', () => {
  it('rates dislike and reveals reason chips', async () => {
    const wrapper = mount(RateControl, { props })
    await wrapper.findAll('.rate__btn')[1].trigger('click') // 👎
    await flushPromises()
    expect(rate).toHaveBeenCalledWith(expect.objectContaining({ rating: -1 }))
    expect(like).not.toHaveBeenCalled()
    expect(wrapper.findAll('.rate__chip').length).toBeGreaterThan(0)
  })

  it('thumbs-up rates +1 and saves a favorite; toggling off un-saves', async () => {
    const wrapper = mount(RateControl, { props })
    const up = wrapper.findAll('.rate__btn')[0]
    await up.trigger('click') // 👍 → rate +1 + save
    await flushPromises()
    expect(rate).toHaveBeenCalledWith(expect.objectContaining({ rating: 1 }))
    expect(like).toHaveBeenCalledWith(props.pattern, props.meta)
    await up.trigger('click') // toggle off → rate 0 + unsave
    await flushPromises()
    expect(rate).toHaveBeenLastCalledWith(expect.objectContaining({ rating: 0 }))
    expect(unlike).toHaveBeenCalledWith('fav1')
  })
})
