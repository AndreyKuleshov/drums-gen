// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'

const state = { authed: true, admin: false, ready: true }
vi.mock('../../lib/auth', () => ({
  useAuth: () => ({
    isAuthenticated: { value: state.authed },
    ready: { value: state.ready },
    refresh: vi.fn(),
    user: { value: state.admin ? { is_admin: true } : { is_admin: false } },
  }),
}))

import { authGuard } from '../index'

const adminRoute = { meta: { requiresAuth: true, requiresAdmin: true }, fullPath: '/admin/ratings' } as never

describe('authGuard', () => {
  it('redirects a non-admin away from an admin route', async () => {
    state.authed = true; state.admin = false
    expect(await authGuard(adminRoute)).toEqual({ name: 'studio' })
  })
  it('allows an admin', async () => {
    state.authed = true; state.admin = true
    expect(await authGuard(adminRoute)).toBe(true)
  })
  it('redirects an anonymous user to login', async () => {
    state.authed = false; state.admin = false
    expect(await authGuard(adminRoute)).toMatchObject({ name: 'login' })
  })
})
