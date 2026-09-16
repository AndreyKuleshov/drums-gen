<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useAuth } from '../lib/auth'
import { adminListUsers, adminSetUserAdmin, type AdminUserRow } from '../lib/adminUsers'

const { user } = useAuth()
const users = ref<AdminUserRow[]>([])
const loading = ref(true)
const error = ref('')
const actionError = ref('')

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

async function toggleAdmin(row: AdminUserRow): Promise<void> {
  actionError.value = ''
  try {
    const updated = await adminSetUserAdmin(row.id, !row.is_admin)
    const i = users.value.findIndex((u) => u.id === updated.id)
    if (i !== -1) users.value[i] = updated
  } catch {
    actionError.value = 'Could not update that user.'
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
      <div class="usertable-wrap">
        <table class="usertable">
          <thead>
            <tr><th>Email</th><th>Name</th><th>Verified</th><th>Admin</th><th>Joined</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in users" :key="row.id">
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
.userbtn {
  padding: 4px 10px; border-radius: var(--r-sm); border: 1px solid var(--edge);
  background: transparent; color: var(--text-dim); font-family: var(--font-mono);
  font-size: 0.64rem; cursor: pointer;
}
.userbtn--on { color: var(--amber-bright); border-color: var(--amber-dim); }
.userbtn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
