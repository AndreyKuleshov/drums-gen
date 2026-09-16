/** Admin API: list users + grant/revoke admin. */
import { apiFetch } from './api'

export interface AdminUserRow {
  id: string
  email: string
  display_name: string
  is_admin: boolean
  is_verified: boolean
  created_at: string
}

export function adminListUsers(): Promise<AdminUserRow[]> {
  return apiFetch<AdminUserRow[]>('/admin/users')
}

export function adminSetUserAdmin(id: string, isAdmin: boolean): Promise<AdminUserRow> {
  return apiFetch<AdminUserRow>(`/admin/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_admin: isAdmin }),
  })
}
