<script setup lang="ts">
import { RouterLink } from 'vue-router'

import AuthNav from '../components/AuthNav.vue'
import { useAuth } from '../lib/auth'

const { user } = useAuth()

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2)
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('') || '?'
}
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">My Account</span>
        </div>
        <div class="brand__meta">
          <span class="brand__model">RG&#8209;40 · RUDIMENT ENGINE</span>
          <RouterLink to="/" class="nav-link">&larr; Generator</RouterLink>
          <AuthNav />
          <span class="led led--on" aria-hidden="true" />
        </div>
      </header>

      <section v-if="user" class="account">
        <div class="account__profile">
          <span v-if="user.avatar_url" class="account__avatar">
            <img :src="user.avatar_url" alt="" />
          </span>
          <span v-else class="account__avatar account__avatar--initials" aria-hidden="true">
            {{ initials(user.display_name) }}
          </span>
          <div class="account__id">
            <h2 class="account__name">{{ user.display_name }}</h2>
            <p class="account__email">{{ user.email }}</p>
            <p v-if="user.bio" class="account__bio">{{ user.bio }}</p>
          </div>
        </div>

        <div class="account__soon">
          <h3 class="account__soon-title">Favorites</h3>
          <p class="account__soon-text">
            Like a pattern on the generator and it'll show up here. Profile editing and your
            saved patterns are landing next.
          </p>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.account {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.account__profile {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 20px;
  border-radius: var(--r-lg);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  box-shadow: var(--shadow-1), var(--inset);
}

.account__avatar {
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  flex: none;
  border-radius: 999px;
  overflow: hidden;
  background: linear-gradient(160deg, var(--amber), var(--amber-dim));
  color: #1a1206;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.5rem;
  box-shadow: 0 0 20px -6px var(--amber-glow);
}

.account__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.account__name {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 600;
  color: var(--text);
}

.account__email {
  margin: 2px 0 0;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-faint);
}

.account__bio {
  margin: 8px 0 0;
  color: var(--text-dim);
  font-size: 0.9rem;
  line-height: 1.5;
}

.account__soon {
  padding: 20px;
  border-radius: var(--r-lg);
  border: 1px dashed var(--edge);
  background: linear-gradient(180deg, #171310, var(--chassis));
}

.account__soon-title {
  margin: 0 0 6px;
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text);
}

.account__soon-text {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.9rem;
  line-height: 1.55;
}
</style>
