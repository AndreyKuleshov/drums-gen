// @vitest-environment jsdom
import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AdminView from './AdminView.vue'

describe('AdminView', () => {
  it('renders Ratings + Users tabs and a router-view outlet', () => {
    const wrapper = mount(AdminView, {
      global: { stubs: { RouterLink: RouterLinkStub, RouterView: true, AuthNav: true } },
    })
    expect(wrapper.text()).toContain('Ratings')
    expect(wrapper.text()).toContain('Users')
    expect(wrapper.find('.admtabs').exists()).toBe(true)
  })
})
