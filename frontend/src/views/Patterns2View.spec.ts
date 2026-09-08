// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

// Stub network + audio so the component mounts in jsdom.
vi.mock('../lib/api', () => ({
  apiFetch: vi.fn().mockResolvedValue({
    time_sig: { num: 4, den: 4 },
    tempo_bpm: 100,
    subdivision: '1/16',
    accent_mode: 'rudiment',
    bars: [],
  }),
}))
vi.mock('../lib/audio', () => ({ playPhrase: vi.fn(), stopPhrase: vi.fn() }))

import Patterns2View from './Patterns2View.vue'

describe('Patterns2View', () => {
  it('renders the three family toggles and a generate button', () => {
    const wrapper = mount(Patterns2View, {
      global: { stubs: { RouterLink: true, TransportRack: true, ScoreView: true } },
    })
    const text = wrapper.text()
    expect(text).toContain('Singles')
    expect(text).toContain('Paradiddle')
    expect(wrapper.find('[data-test="generate"]').exists()).toBe(true)
  })
})
