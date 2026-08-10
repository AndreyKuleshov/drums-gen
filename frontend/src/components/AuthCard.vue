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

      <!-- The lit cream display — the same console screen the generator uses -->
      <div class="authscreen">
        <h1 class="authscreen__title">
          {{ title }}<span class="authscreen__caret" aria-hidden="true" />
        </h1>
      </div>

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
  padding: 20px 22px 26px;
  border-radius: var(--r-xl);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--chassis), var(--panel));
  box-shadow: var(--shadow-3), var(--inset);
}

.authcard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.authcard__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  text-decoration: none;
}

.authcard__mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex: none;
  border-radius: var(--r-sm);
  background: linear-gradient(160deg, var(--amber), var(--amber-dim));
  color: #1a1206;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.8rem;
  box-shadow: 0 0 14px -2px var(--amber-glow);
}

.authcard__model {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.14em;
  color: var(--text-faint);
}

/* Lit cream display: mirrors the generator's .screen__glass material. */
.authscreen {
  border-radius: var(--r-md);
  padding: 16px 18px;
  background: linear-gradient(180deg, #fbf6ec, var(--screen));
  border: 1px solid var(--screen-edge);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.4),
    inset 0 2px 12px rgba(120, 96, 60, 0.16),
    0 0 20px -8px var(--amber-glow);
}

.authscreen__title {
  margin: 0;
  display: flex;
  align-items: baseline;
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--ink);
}

.authscreen__caret {
  display: inline-block;
  width: 9px;
  height: 1.05em;
  margin-left: 6px;
  transform: translateY(0.12em);
  background: var(--amber-dim);
  animation: auth-caret 1.1s steps(1) infinite;
}

@keyframes auth-caret {
  0%,
  50% {
    opacity: 1;
  }
  50.01%,
  100% {
    opacity: 0;
  }
}

.authcard__subtitle {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.9rem;
  line-height: 1.55;
}

@media (prefers-reduced-motion: reduce) {
  .authscreen__caret {
    animation: none;
    opacity: 0.7;
  }
}
</style>
