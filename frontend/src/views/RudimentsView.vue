<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import AuthNav from '../components/AuthNav.vue'
import RudimentStaff from '../components/RudimentStaff.vue'
import { apiUrl } from '../lib/api'
import type { Rudiment } from '../types'

const rudiments = ref<Rudiment[]>([])
const error = ref('')
const loading = ref(true)

const tiers = [
  { key: 'beginner', label: 'Beginner', note: 'single & double strokes, the basic paradiddle' },
  { key: 'mid', label: 'Mid', note: 'longer paradiddles and rolls' },
  { key: 'pro', label: 'Pro', note: 'flams and drags — the full vocabulary' },
] as const

const byTier = computed(() =>
  tiers.map((t) => ({ ...t, items: rudiments.value.filter((r) => r.difficulty === t.key) })),
)

onMounted(async () => {
  try {
    const resp = await fetch(apiUrl('/rudiments'))
    if (!resp.ok) throw new Error(String(resp.status))
    rudiments.value = (await resp.json()) as Rudiment[]
  } catch {
    error.value = 'Can’t reach the engine. Is the backend running?'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">Rudiment Reference</span>
        </div>
        <div class="brand__meta">
          <span class="brand__model">RG&#8209;40 · RUDIMENT ENGINE</span>
          <RouterLink to="/" class="nav-link">&larr; Generator</RouterLink>
          <AuthNav />
          <span class="led led--on" aria-hidden="true" />
        </div>
      </header>

      <p class="intro">
        The vocabulary the engine draws from, by difficulty. Each level also
        includes everything easier.
      </p>

      <ul class="legend">
        <li class="legend__item">
          <RudimentStaff :sticking="['R']" :accents="[true]" :grace="[0]" :clef="false" hide-labels />
          <span class="legend__text">Accent — <code>&gt;</code> above the note</span>
        </li>
        <li class="legend__item">
          <RudimentStaff :sticking="['R']" :accents="[false]" :grace="[1]" :clef="false" hide-labels />
          <span class="legend__text">Flam — one grace note</span>
        </li>
        <li class="legend__item">
          <RudimentStaff :sticking="['R']" :accents="[false]" :grace="[2]" :clef="false" hide-labels />
          <span class="legend__text">Drag — two grace notes</span>
        </li>
      </ul>

      <p v-if="loading" class="state">Loading…</p>
      <p v-else-if="error" class="state state--error" role="alert">{{ error }}</p>

      <section v-for="tier in byTier" v-else :key="tier.key" class="tier">
        <h2 class="tier__title">
          {{ tier.label }}
          <span class="tier__note">{{ tier.note }}</span>
        </h2>

        <ul class="rudlist">
          <li v-for="r in tier.items" :key="r.id" class="rud">
            <div class="rud__head">
              <span class="rud__name">{{ r.name }}</span>
              <span v-if="r.filler" class="rud__tag">filler</span>
            </div>
            <div class="rudscreen">
              <RudimentStaff :sticking="r.sticking" :accents="r.accents" :grace="r.grace" />
            </div>
          </li>
        </ul>
      </section>
    </div>
  </main>
</template>

<style scoped>
.intro {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.92rem;
  line-height: 1.6;
}

.legend {
  list-style: none;
  margin: 0;
  padding: 12px 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px 26px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge-soft);
  background: linear-gradient(180deg, #171310, var(--chassis));
  box-shadow: var(--inset);
}

.legend__item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.legend__text {
  font-size: 0.82rem;
  color: var(--text-dim);
}

.state {
  color: var(--text-dim);
}

.state--error {
  color: var(--danger);
}

.tier {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tier__title {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
  margin: 6px 0 0;
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text);
}

.tier__note {
  font-family: var(--font-mono);
  font-size: 0.66rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.rudlist {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.rud {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--r-lg);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  box-shadow: var(--shadow-1), inset 0 1px 0 rgba(239, 231, 216, 0.04);
}

.rud__head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rud__name {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--text);
}

.rud__tag {
  font-family: var(--font-mono);
  font-size: 0.56rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-faint);
  border: 1px solid var(--edge);
  border-radius: var(--r-sm);
  padding: 2px 6px;
}

/* Holds the mini-notation; scrolls if a dense rudiment is wider than the card. */
.rudscreen {
  overflow-x: auto;
  max-width: 100%;
}

.legend__text code {
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: var(--amber-bright);
}
</style>
