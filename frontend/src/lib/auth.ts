/**
 * Auth state, shared app-wide via a module-level ref (keeps the no-Pinia
 * footprint). `refresh()` is called once on app start to hydrate from the
 * session cookie; the auth views call login/register/logout.
 */
import { computed, ref } from 'vue'

import { apiFetch, ApiError } from './api'
import type { User } from '../types'

const user = ref<User | null>(null)
const ready = ref(false)

export function useAuth() {
  async function refresh(): Promise<void> {
    try {
      user.value = await apiFetch<User>('/auth/me')
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) user.value = null
      else user.value = null
    } finally {
      ready.value = true
    }
  }

  async function login(email: string, password: string): Promise<void> {
    user.value = await apiFetch<User>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async function register(email: string, password: string, displayName: string): Promise<void> {
    await apiFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    })
  }

  async function verify(token: string): Promise<void> {
    user.value = await apiFetch<User>('/auth/verify', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
  }

  async function forgot(email: string): Promise<void> {
    await apiFetch('/auth/forgot', { method: 'POST', body: JSON.stringify({ email }) })
  }

  async function reset(token: string, password: string): Promise<void> {
    await apiFetch('/auth/reset', {
      method: 'POST',
      body: JSON.stringify({ token, password }),
    })
  }

  async function logout(): Promise<void> {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } finally {
      user.value = null
    }
  }

  function setUser(next: User): void {
    user.value = next
  }

  return {
    user: computed(() => user.value),
    isAuthenticated: computed(() => user.value !== null),
    ready: computed(() => ready.value),
    refresh,
    login,
    register,
    verify,
    forgot,
    reset,
    logout,
    setUser,
  }
}
