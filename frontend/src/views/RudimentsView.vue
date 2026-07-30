<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

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
          <span class="led led--on" aria-hidden="true" />
        </div>
      </header>

      <p class="intro">
        The vocabulary the engine draws from, by difficulty. Each level also
        includes everything easier. Legend:
        <span class="legend"><span class="legend__acc">&gt;</span> accent</span>
        <span class="legend"><span class="legend__grace">•</span> flam</span>
        <span class="legend"><span class="legend__grace">••</span> drag</span>
      </p>

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
            <ol class="sticking" :aria-label="`${r.name} sticking`">
              <li
                v-for="(hand, i) in r.sticking"
                :key="i"
                :class="['key', { 'key--accent': r.accents[i] }]"
              >
                <span class="key__acc" aria-hidden="true">{{ r.accents[i] ? '>' : '' }}</span>
                <span class="key__letter">{{ hand }}</span>
                <span v-if="r.grace[i]" class="key__grace" :aria-label="r.grace[i] === 1 ? 'flam' : 'drag'">
                  {{ r.grace[i] === 1 ? '•' : '••' }}
                </span>
              </li>
            </ol>
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
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
  margin-left: 14px;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  color: var(--text-faint);
}

.legend__acc,
.legend__grace {
  color: var(--amber-bright);
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

.sticking {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.key {
  position: relative;
  display: grid;
  place-items: center;
  min-width: 30px;
  height: 34px;
  border-radius: var(--r-sm);
  border: 1px solid var(--edge);
  background: #100e0c;
  box-shadow: var(--inset);
  font-family: var(--font-mono);
  font-size: 0.95rem;
  color: var(--text-dim);
}

.key--accent {
  color: #221204;
  background: linear-gradient(180deg, var(--amber-bright), var(--amber));
  border-color: var(--amber-dim);
  box-shadow: var(--shadow-1), 0 0 10px -4px var(--amber-glow);
}

.key__acc {
  position: absolute;
  top: -14px;
  height: 12px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--amber-bright);
}

.key__grace {
  position: absolute;
  top: 1px;
  left: 3px;
  font-size: 0.5rem;
  line-height: 1;
  letter-spacing: -1px;
  color: var(--amber-bright);
}

.key--accent .key__grace {
  color: #4a2a08;
}
</style>
