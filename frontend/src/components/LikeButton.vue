<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuth } from '../lib/auth'
import { likePattern } from '../lib/patterns'
import type { Phrase } from '../types'

const props = defineProps<{ phrase: Phrase; meta: Record<string, unknown> }>()

const router = useRouter()
const { isAuthenticated } = useAuth()

const state = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')

// A fresh generation resets the button to its unsaved state.
watch(
  () => props.phrase,
  () => {
    state.value = 'idle'
  },
)

async function onClick(): Promise<void> {
  if (!isAuthenticated.value) {
    await router.push({ name: 'login', query: { next: '/' } })
    return
  }
  if (state.value === 'saving' || state.value === 'saved') return
  state.value = 'saving'
  try {
    await likePattern(props.phrase, props.meta)
    state.value = 'saved'
  } catch {
    state.value = 'error'
  }
}
</script>

<template>
  <button
    class="like"
    :class="{ 'like--saved': state === 'saved' }"
    type="button"
    :title="isAuthenticated ? 'Save to favorites' : 'Sign in to save'"
    :aria-pressed="state === 'saved'"
    @click="onClick"
  >
    <svg viewBox="0 0 24 24" class="like__heart" aria-hidden="true">
      <path
        d="M12 21s-7.5-4.6-10-9.2C.4 8.6 1.6 5.2 4.8 4.3c2-.6 3.9.3 5 1.9 1.1-1.6 3-2.5 5-1.9 3.2.9 4.4 4.3 2.8 7.5C19.5 16.4 12 21 12 21z"
      />
    </svg>
    <span class="like__label">{{
      state === 'saved' ? 'Saved' : state === 'saving' ? 'Saving…' : 'Save'
    }}</span>
  </button>
</template>

<style scoped>
.like {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 13px;
  border-radius: 999px;
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  box-shadow: var(--shadow-1);
  transition:
    color 0.15s ease,
    box-shadow 0.18s ease;
}

.like:hover {
  color: var(--amber-bright);
  box-shadow: var(--shadow-1), inset 0 0 0 1px rgba(255, 157, 60, 0.22);
}

.like__heart {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  transition: fill 0.2s ease;
}

.like--saved {
  color: var(--amber-bright);
  border-color: var(--amber-dim);
}

.like--saved .like__heart {
  fill: var(--amber);
  stroke: var(--amber);
}
</style>
