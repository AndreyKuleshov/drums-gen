// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

// `rows`/`setAdmin`/`setBlocked` must be declared inside `vi.hoisted` (not as
// plain top-level `const`s): the mocked module is a dependency of
// `AdminUsersView.vue`, so ESM evaluates its `vi.mock` factory before this test
// file's own top-level code runs. A plain `const rows = [...]` below the factory
// would still be in its temporal dead zone when the factory dereferences it
// eagerly via `.mockResolvedValue(rows)`.
const { rows, setAdmin, setBlocked } = vi.hoisted(() => {
  // Explicit, deterministic `created_at` values (not sequential `new Date()`
  // calls): AdminUsersView sorts by `created_at` desc by default, so real
  // millisecond timing differences between rows would nondeterministically
  // reorder them and break the own-row-disabled index assertion below. `me`
  // is deliberately the newest so it sorts first, matching the assertions.
  const rows = [
    { id: 'me', email: 'me@x.io', display_name: 'Me', is_admin: true, is_verified: true, is_blocked: false, blocked_at: null, created_at: '2024-01-04T00:00:00.000Z' },
    { id: 'other', email: 'o@x.io', display_name: 'Other', is_admin: false, is_verified: true, is_blocked: false, blocked_at: null, created_at: '2024-01-03T00:00:00.000Z' },
    { id: 'x', email: 'zzz@x.io', display_name: 'Zed', is_admin: false, is_verified: true, is_blocked: false, blocked_at: null, created_at: '2024-01-02T00:00:00.000Z' },
    { id: 'w', email: 'pending@x.io', display_name: 'Pend', is_admin: false, is_verified: false, is_blocked: true, blocked_at: '2024-02-01T00:00:00.000Z', created_at: '2024-01-01T00:00:00.000Z' },
  ]
  const setAdmin = vi.fn().mockResolvedValue({ ...rows[1], is_admin: true })
  const setBlocked = vi.fn().mockResolvedValue({ ...rows[1], is_blocked: true, blocked_at: '2024-02-02T00:00:00.000Z' })
  return { rows, setAdmin, setBlocked }
})
vi.mock('../lib/adminUsers', () => ({
  adminListUsers: vi.fn().mockResolvedValue(rows),
  adminSetUserAdmin: (...a: unknown[]) => setAdmin(...a),
  adminSetUserBlocked: (...a: unknown[]) => setBlocked(...a),
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
  it('disables own-row actions and toggles admin + block on another user', async () => {
    const wrapper = mount(AdminUsersView, opts)
    await flushPromises()
    expect(wrapper.text()).toContain('o@x.io')

    // Rows sort by created_at desc: [me, other, x, w]. Each row has an admin
    // button and a block button; both of the own row (me) are disabled.
    const bodyRows = wrapper.findAll('tbody tr')
    const meBtns = bodyRows[0].findAll('.userbtn')
    expect((meBtns[0].element as HTMLButtonElement).disabled).toBe(true) // admin
    expect((meBtns[1].element as HTMLButtonElement).disabled).toBe(true) // block

    const otherBtns = bodyRows[1].findAll('.userbtn')
    await otherBtns[0].trigger('click')
    expect(setAdmin).toHaveBeenCalledWith('other', true)
    await otherBtns[1].trigger('click')
    expect(setBlocked).toHaveBeenCalledWith('other', true)

    await wrapper.find('[data-test="user-filter"]').setValue('zzz')
    await flushPromises()
    expect(wrapper.text()).toContain('zzz@x.io')
    expect(wrapper.text()).not.toContain('o@x.io')
  })

  it('filters by verified and active status', async () => {
    const wrapper = mount(AdminUsersView, opts)
    await flushPromises()

    // Only the unverified user (w) remains when filtering unverified.
    await wrapper.find('[data-test="filter-verified"]').setValue('no')
    await flushPromises()
    expect(wrapper.text()).toContain('pending@x.io')
    expect(wrapper.text()).not.toContain('o@x.io')

    // Reset, then filter to blocked-only — again only w (the blocked user).
    await wrapper.find('[data-test="filter-verified"]').setValue('all')
    await wrapper.find('[data-test="filter-active"]').setValue('blocked')
    await flushPromises()
    expect(wrapper.text()).toContain('pending@x.io')
    expect(wrapper.text()).not.toContain('zzz@x.io')

    // Active-only hides the blocked user.
    await wrapper.find('[data-test="filter-active"]').setValue('active')
    await flushPromises()
    expect(wrapper.text()).not.toContain('pending@x.io')
    expect(wrapper.text()).toContain('zzz@x.io')
  })
})
