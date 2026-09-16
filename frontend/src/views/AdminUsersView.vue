<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuth } from '../lib/auth'
import {
  adminListUsers,
  adminSetUserAdmin,
  adminSetUserBlocked,
  type AdminUserRow,
} from '../lib/adminUsers'

const { user } = useAuth()
const users = ref<AdminUserRow[]>([])
const loading = ref(true)
const error = ref('')
const actionError = ref('')

const query = ref('')
const verifiedFilter = ref<'all' | 'yes' | 'no'>('all')
const activeFilter = ref<'all' | 'active' | 'blocked'>('all')
const busyId = ref<string | null>(null)

type UKey = 'email' | 'display_name' | 'is_verified' | 'is_admin' | 'is_blocked' | 'created_at'
const sortKey = ref<UKey>('created_at')
const sortDir = ref<1 | -1>(-1)

function toggleSort(key: UKey): void {
  if (sortKey.value === key) sortDir.value = sortDir.value === 1 ? -1 : 1
  else {
    sortKey.value = key
    sortDir.value = 1
  }
}

const visibleUsers = computed(() => {
  const q = query.value.trim().toLowerCase()
  const filtered = users.value.filter((u) => {
    if (q && !u.email.toLowerCase().includes(q) && !u.display_name.toLowerCase().includes(q))
      return false
    if (verifiedFilter.value === 'yes' && !u.is_verified) return false
    if (verifiedFilter.value === 'no' && u.is_verified) return false
    if (activeFilter.value === 'active' && u.is_blocked) return false
    if (activeFilter.value === 'blocked' && !u.is_blocked) return false
    return true
  })
  return [...filtered].sort((a, b) => {
    const av = String(a[sortKey.value] ?? '')
    const bv = String(b[sortKey.value] ?? '')
    return av < bv ? -sortDir.value : av > bv ? sortDir.value : 0
  })
})

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    users.value = await adminListUsers()
  } catch {
    error.value = 'Could not load users.'
  } finally {
    loading.value = false
  }
}

function replaceRow(updated: AdminUserRow): void {
  const i = users.value.findIndex((u) => u.id === updated.id)
  if (i !== -1) users.value[i] = updated
}

async function toggleAdmin(row: AdminUserRow): Promise<void> {
  actionError.value = ''
  try {
    replaceRow(await adminSetUserAdmin(row.id, !row.is_admin))
  } catch {
    actionError.value = 'Could not update that user.'
  }
}

async function toggleBlock(row: AdminUserRow): Promise<void> {
  actionError.value = ''
  busyId.value = row.id
  try {
    replaceRow(await adminSetUserBlocked(row.id, !row.is_blocked))
  } catch {
    actionError.value = 'Could not update that user.'
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <section>
    <p v-if="loading" class="usersmsg">Loading…</p>
    <p v-else-if="error" class="usersmsg" role="alert">{{ error }}</p>

    <div v-else>
      <p v-if="actionError" class="usersmsg" role="alert">{{ actionError }}</p>
      <div class="userfilters">
        <input
          v-model="query"
          class="userfilter"
          type="text"
          data-test="user-filter"
          placeholder="filter by email or name"
          aria-label="Filter users"
        />
        <label class="userfilter__sel">
          Verified
          <select v-model="verifiedFilter" data-test="filter-verified" aria-label="Verified filter">
            <option value="all">All</option>
            <option value="yes">Verified</option>
            <option value="no">Unverified</option>
          </select>
        </label>
        <label class="userfilter__sel">
          Status
          <select v-model="activeFilter" data-test="filter-active" aria-label="Active filter">
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="blocked">Blocked</option>
          </select>
        </label>
      </div>
      <div class="usertable-wrap">
        <table class="usertable">
          <thead>
            <tr>
              <th class="is-sortable" @click="toggleSort('email')">Email</th>
              <th class="is-sortable" @click="toggleSort('display_name')">Name</th>
              <th class="is-sortable" @click="toggleSort('is_verified')">Verified</th>
              <th class="is-sortable" @click="toggleSort('is_admin')">Admin</th>
              <th class="is-sortable" @click="toggleSort('is_blocked')">Status</th>
              <th class="is-sortable" @click="toggleSort('created_at')">Joined</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in visibleUsers" :key="row.id" :class="{ 'is-blocked': row.is_blocked }">
              <td>{{ row.email }}</td>
              <td>{{ row.display_name }}</td>
              <td>{{ row.is_verified ? '✓' : '—' }}</td>
              <td>
                <button
                  type="button"
                  class="userbtn"
                  :class="{ 'userbtn--on': row.is_admin }"
                  :disabled="row.id === user?.id"
                  :title="row.id === user?.id ? 'Cannot change your own admin' : ''"
                  @click="toggleAdmin(row)"
                >
                  {{ row.is_admin ? 'Admin ✓' : 'Make admin' }}
                </button>
              </td>
              <td>
                <button
                  type="button"
                  class="userbtn"
                  :class="{ 'userbtn--danger': row.is_blocked }"
                  :disabled="row.id === user?.id || busyId === row.id"
                  :title="row.id === user?.id ? 'You cannot block yourself' : ''"
                  @click="toggleBlock(row)"
                >
                  {{ row.is_blocked ? 'Blocked · Unblock' : 'Block' }}
                </button>
              </td>
              <td>{{ new Date(row.created_at).toLocaleDateString() }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.usersmsg { color: var(--text-dim); font-size: 0.9rem; }
.usertable-wrap { overflow-x: auto; }
.usertable { width: 100%; border-collapse: collapse; font-size: 0.78rem; }
.usertable th, .usertable td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--edge); }
.usertable tr.is-blocked td { opacity: 0.55; }
.userbtn {
  padding: 4px 10px; border-radius: var(--r-sm); border: 1px solid var(--edge);
  background: transparent; color: var(--text-dim); font-family: var(--font-mono);
  font-size: 0.64rem; cursor: pointer;
}
.userbtn--on { color: var(--amber-bright); border-color: var(--amber-dim); }
.userbtn--danger { color: var(--danger); border-color: var(--danger); opacity: 1; }
.usertable tr.is-blocked td .userbtn--danger { opacity: 1; }
.userbtn:disabled { opacity: 0.5; cursor: not-allowed; }
.userfilters { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 10px; }
.userfilter {
  padding: 5px 8px; border-radius: var(--r-sm); border: 1px solid var(--edge);
  background: var(--field-ink); color: var(--text); font-size: 0.74rem; min-width: 240px;
}
.userfilter__sel {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--font-mono); font-size: 0.62rem; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--text-faint);
}
.userfilter__sel select {
  padding: 4px 6px; border-radius: var(--r-sm); border: 1px solid var(--edge);
  background: var(--field-ink); color: var(--text); font-size: 0.74rem;
  text-transform: none; letter-spacing: normal;
}
.usertable th.is-sortable { cursor: pointer; user-select: none; }
.usertable th.is-sortable:hover { color: var(--amber-bright); }
</style>
