<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'

import AuthNav from '../components/AuthNav.vue'

const router = useRouter()

// Go back to wherever the admin came from; fall back to the generator if the
// admin page was opened directly (no in-app history to step back to).
function goBack(): void {
  if (window.history.state?.back) router.back()
  else router.push('/')
}
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">Admin</span>
        </div>
        <div class="brand__meta">
          <button type="button" class="nav-link" @click="goBack">&larr; Back</button>
          <AuthNav />
          <span class="led led--on" aria-hidden="true" />
        </div>
      </header>

      <nav class="admtabs" aria-label="Admin sections">
        <RouterLink to="/admin/ratings" class="admtabs__tab">Ratings</RouterLink>
        <RouterLink to="/admin/users" class="admtabs__tab">Users</RouterLink>
      </nav>

      <RouterView />
    </div>
  </main>
</template>

<style scoped>
.admtabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--edge);
  margin-bottom: 4px;
}
.admtabs__tab {
  padding: 8px 14px;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-dim);
  text-decoration: none;
  border-bottom: 2px solid transparent;
}
.admtabs__tab:hover {
  color: var(--amber-bright);
}
.admtabs__tab.router-link-active {
  color: var(--amber-bright);
  border-bottom-color: var(--amber-dim);
}
</style>
