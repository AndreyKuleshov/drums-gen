<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { useAuth } from '../lib/auth'

const router = useRouter()
const { user, isAuthenticated, ready, logout } = useAuth()

const open = ref(false)

async function signOut(): Promise<void> {
  open.value = false
  await logout()
  await router.push('/')
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2)
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('') || '?'
}
</script>

<template>
  <div v-if="ready" class="authnav">
    <template v-if="!isAuthenticated">
      <RouterLink to="/login" class="nav-link">Sign in</RouterLink>
    </template>

    <div v-else class="authnav__menu">
      <button
        class="authnav__trigger"
        type="button"
        :aria-expanded="open"
        aria-haspopup="menu"
        @click="open = !open"
      >
        <span v-if="user?.avatar_url" class="authnav__avatar">
          <img :src="user.avatar_url" alt="" />
        </span>
        <span v-else class="authnav__avatar authnav__avatar--initials" aria-hidden="true">
          {{ initials(user?.display_name ?? '?') }}
        </span>
        <span class="authnav__name">{{ user?.display_name }}</span>
      </button>

      <div v-if="open" class="authnav__pop" role="menu" @click="open = false">
        <RouterLink to="/account" class="authnav__item" role="menuitem">Account</RouterLink>
        <button class="authnav__item" type="button" role="menuitem" @click="signOut">
          Sign out
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.authnav {
  display: flex;
  align-items: center;
}

.authnav__menu {
  position: relative;
}

.authnav__trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px 5px 5px;
  border-radius: 999px;
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  cursor: pointer;
  box-shadow: var(--shadow-1);
  transition:
    color 0.15s ease,
    box-shadow 0.18s ease;
}

.authnav__trigger:hover {
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), inset 0 0 0 1px rgba(255, 157, 60, 0.22);
}

.authnav__avatar {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 999px;
  overflow: hidden;
  background: linear-gradient(160deg, var(--amber), var(--amber-dim));
  color: #1a1206;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.68rem;
}

.authnav__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.authnav__name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.authnav__pop {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  z-index: 20;
  min-width: 160px;
  display: flex;
  flex-direction: column;
  padding: 6px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--panel));
  box-shadow: var(--shadow-3);
}

.authnav__item {
  display: block;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text-dim);
  font-family: var(--font-ui);
  font-size: 0.88rem;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
}

.authnav__item:hover {
  background: rgba(255, 157, 60, 0.1);
  color: var(--amber-bright);
}
</style>
