// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const playPhrase = vi.fn().mockResolvedValue(undefined)
const playGroove = vi.fn().mockResolvedValue(undefined)
vi.mock('../lib/audio', () => ({ playPhrase: (...a: unknown[]) => playPhrase(...a), stopPhrase: vi.fn() }))
vi.mock('../lib/kit', () => ({ playGroove: (...a: unknown[]) => playGroove(...a), stopGroove: vi.fn() }))

import RatingPreviewModal from './RatingPreviewModal.vue'

const opts = { global: { stubs: { ScoreView: true, GrooveScore: true, teleport: true } } }

describe('RatingPreviewModal', () => {
  it('renders a groove and plays it', async () => {
    const wrapper = mount(RatingPreviewModal, { props: { kind: 'pattern', pattern: { bars: [] }, tempo: 100 }, ...opts })
    expect(wrapper.html()).toContain('groove-score') // stubbed GrooveScore rendered
    await wrapper.find('.ratebtn').trigger('click')
    expect(playGroove).toHaveBeenCalled()
  })

  it('renders a phrase and plays it', async () => {
    const wrapper = mount(RatingPreviewModal, { props: { kind: 'exercise', pattern: { bars: [] }, tempo: 100 }, ...opts })
    expect(wrapper.html()).toContain('score-view') // stubbed ScoreView rendered
    await wrapper.find('.ratebtn').trigger('click')
    expect(playPhrase).toHaveBeenCalled()
  })
})
