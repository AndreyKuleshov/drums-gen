// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../lib/auth', () => ({ useAuth: () => ({ isAuthenticated: { value: true } }) }))
const rate = vi.fn().mockResolvedValue(undefined)
vi.mock('../lib/ratings', () => ({ ratePattern: (...a: unknown[]) => rate(...a) }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

import RateControl from './RateControl.vue'

describe('RateControl', () => {
  it('rates dislike and reveals reason chips', async () => {
    const wrapper = mount(RateControl, {
      props: { pattern: { a: 1 }, kind: 'exercise', params: {}, seed: null },
    })
    const thumbs = wrapper.findAll('.rate__btn')
    await thumbs[1].trigger('click') // 👎
    expect(rate).toHaveBeenCalledWith(expect.objectContaining({ rating: -1 }))
    expect(wrapper.findAll('.rate__chip').length).toBeGreaterThan(0)
  })
})
