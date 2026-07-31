<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <main class="authstage">
    <div class="authcard">
      <header class="authcard__head">
        <RouterLink to="/" class="authcard__brand">
          <span class="authcard__mark" aria-hidden="true">RG</span>
          <span class="authcard__model">RG&#8209;40 · RUDIMENT ENGINE</span>
        </RouterLink>
        <span class="led led--on" aria-hidden="true" />
      </header>

      <h1 class="authcard__title">{{ title }}</h1>
      <p v-if="subtitle" class="authcard__subtitle">{{ subtitle }}</p>

      <slot />
    </div>
  </main>
</template>

<style scoped>
.authstage {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: 32px 20px;
}

.authcard {
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 26px 26px 30px;
  border-radius: var(--r-xl);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--chassis), var(--panel));
  box-shadow: var(--shadow-3), var(--inset);
}

.authcard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.authcard__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}

.authcard__mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: var(--r-sm);
  background: linear-gradient(160deg, var(--amber), var(--amber-dim));
  color: #1a1206;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.8rem;
  box-shadow: 0 0 14px -2px var(--amber-glow);
}

.authcard__model {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.14em;
  color: var(--text-faint);
}

.authcard__title {
  margin: 6px 0 0;
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text);
}

.authcard__subtitle {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.9rem;
  line-height: 1.55;
}
</style>
