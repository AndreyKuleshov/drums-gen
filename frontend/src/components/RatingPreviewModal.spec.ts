// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const playPhrase = vi.fn().mockResolvedValue(undefined)
const playGroove = vi.fn().mockResolvedValue(undefined)
vi.mock('../lib/audio', () => ({
  playPhrase: (...a: unknown[]) => playPhrase(...a),
  stopPhrase: vi.fn(),
  parseFraction: () => 0.25,
  setMetroSub: vi.fn(),
  setMetronomeVolume: vi.fn(),
  setPatternVolume: vi.fn(),
}))
vi.mock('../lib/kit', () => ({ playGroove: (...a: unknown[]) => playGroove(...a), stopGroove: vi.fn() }))

import RatingPreviewModal from './RatingPreviewModal.vue'

const opts = { global: { stubs: { ScoreView: true, GrooveScore: true, teleport: true } } }

describe('RatingPreviewModal', () => {
  it('renders a groove and plays it with a step callback + metronome flag', async () => {
    const wrapper = mount(RatingPreviewModal, {
      props: { kind: 'pattern', pattern: { bars: [] }, tempo: 100, ver: '2026-09-15', rater: 'a@b.c' },
      ...opts,
    })
    expect(wrapper.html()).toContain('groove-score')
    expect(wrapper.text()).toContain('a@b.c') // header shows the rater
    expect(wrapper.text().toLowerCase()).toContain('pattern') // header shows the kind
    await wrapper.find('[data-test="metronome"]').setValue(true)
    await wrapper.find('.ratebtn').trigger('click') // Play
    expect(playGroove).toHaveBeenCalled()
    const passedOpts = playGroove.mock.calls[0][1] as Record<string, unknown>
    expect(typeof passedOpts.onStep).toBe('function')
    expect(passedOpts.metronome).toBe(true)
  })

  it('renders a phrase and plays it', async () => {
    const wrapper = mount(RatingPreviewModal, {
      props: { kind: 'exercise', pattern: { bars: [] }, tempo: 100, ver: '2026-09-15', rater: 'a@b.c' },
      ...opts,
    })
    expect(wrapper.html()).toContain('score-view')
    await wrapper.find('.ratebtn').trigger('click')
    expect(playPhrase).toHaveBeenCalled()
  })
})
