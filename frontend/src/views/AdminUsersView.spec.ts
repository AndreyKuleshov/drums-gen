// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

// `rows`/`setAdmin` must be declared inside `vi.hoisted` (not as plain top-level
// `const`s): the mocked module is a dependency of `AdminUsersView.vue`, so ESM
// evaluates its `vi.mock` factory before this test file's own top-level code runs.
// A plain `const rows = [...]` below the factory would still be in its temporal
// dead zone when the factory dereferences it eagerly via `.mockResolvedValue(rows)`.
const { rows, setAdmin } = vi.hoisted(() => {
  const rows = [
    { id: 'me', email: 'me@x.io', display_name: 'Me', is_admin: true, is_verified: true, created_at: new Date().toISOString() },
    { id: 'other', email: 'o@x.io', display_name: 'Other', is_admin: false, is_verified: true, created_at: new Date().toISOString() },
  ]
  const setAdmin = vi.fn().mockResolvedValue({ ...rows[1], is_admin: true })
  return { rows, setAdmin }
})
vi.mock('../lib/adminUsers', () => ({
  adminListUsers: vi.fn().mockResolvedValue(rows),
  adminSetUserAdmin: (...a: unknown[]) => setAdmin(...a),
}))
// `user` is used in the template (`user?.id`), which auto-unwraps refs — so the
// mock must return a real ref, not a plain { value } object.
vi.mock('../lib/auth', async () => {
  const { ref } = await import('vue')
  return { useAuth: () => ({ user: ref({ id: 'me' }) }) }
})

import AdminUsersView from './AdminUsersView.vue'

const opts = { global: { stubs: { RouterLink: true, AuthNav: true } } }

describe('AdminUsersView', () => {
  it('lists users, disables the own-row toggle, toggles another user', async () => {
    const wrapper = mount(AdminUsersView, opts)
    await flushPromises()
    expect(wrapper.text()).toContain('o@x.io')
    const buttons = wrapper.findAll('.userbtn')
    // Row order matches `rows`: [me, other]. Own row (me) toggle is disabled.
    expect((buttons[0].element as HTMLButtonElement).disabled).toBe(true)
    await buttons[1].trigger('click')
    expect(setAdmin).toHaveBeenCalledWith('other', true)
  })
})
