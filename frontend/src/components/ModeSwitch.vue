<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <nav class="modeswitch" aria-label="Mode">
    <RouterLink to="/" class="modeswitch__opt" :class="{ 'modeswitch__opt--on': route.path === '/' }">
      Pattern
    </RouterLink>
    <RouterLink
      to="/exercises"
      class="modeswitch__opt"
      :class="{ 'modeswitch__opt--on': route.path === '/exercises' }"
    >
      Exercises
    </RouterLink>
  </nav>
</template>

<style scoped>
.modeswitch {
  display: inline-flex;
  padding: 3px;
  gap: 2px;
  border-radius: 999px;
  border: 1px solid var(--edge);
  background: #100e0c;
  box-shadow: var(--inset);
}

.modeswitch__opt {
  padding: 6px 14px;
  border-radius: 999px;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.64rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  text-decoration: none;
  transition:
    color 0.15s ease,
    background 0.15s ease;
}

.modeswitch__opt--on {
  color: #1a1206;
  background: linear-gradient(180deg, var(--amber), var(--amber-dim));
  box-shadow: 0 0 14px -4px var(--amber-glow);
}
</style>
