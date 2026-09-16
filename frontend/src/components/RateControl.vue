<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuth } from '../lib/auth'
import { likePattern, unlikePattern } from '../lib/patterns'
import { ratePattern, type RatingTag } from '../lib/ratings'

const props = defineProps<{
  pattern: unknown
  kind: 'exercise' | 'pattern'
  params: Record<string, unknown>
  seed: number | null
  meta: Record<string, unknown>
}>()

const router = useRouter()
const { isAuthenticated } = useAuth()

const DISLIKE_TAGS: RatingTag[] = ['too_busy', 'boring', 'unmusical', 'awkward_sticking', 'repetitive', 'too_hard']
const LIKE_TAGS: RatingTag[] = ['groovy', 'creative', 'playable']

const rating = ref<0 | 1 | -1>(0)
const tags = ref<RatingTag[]>([])
const note = ref('')
const busy = ref(false)
const savedId = ref<string | null>(null)

// A new pattern is a new data point — reset the control. The previously-saved
// favorite (if any) persists on its own; it's not tied to this control instance.
watch(
  () => props.pattern,
  () => {
    rating.value = 0
    tags.value = []
    note.value = ''
    savedId.value = null
  },
)

async function submit(): Promise<void> {
  busy.value = true
  try {
    await ratePattern({
      rating: rating.value,
      tags: tags.value,
      note: note.value.trim() || null,
      kind: props.kind,
      pattern: props.pattern,
      params: props.params,
      seed: props.seed,
    })
  } finally {
    busy.value = false
  }
}

// Save/unsave the favorite on the RATING VALUE transition only — chip toggles
// and note edits just re-POST the rating and must never touch the favorite.
async function syncFavorite(): Promise<void> {
  if (rating.value === 1 && savedId.value === null) {
    const saved = await likePattern(props.pattern, props.meta)
    savedId.value = saved.id
  } else if (rating.value !== 1 && savedId.value !== null) {
    const id = savedId.value
    savedId.value = null
    await unlikePattern(id)
  }
}

async function setRating(value: 1 | -1): Promise<void> {
  if (!isAuthenticated.value) {
    await router.push({ name: 'login', query: { next: '/patterns2', reason: 'rate' } })
    return
  }
  if (rating.value === value) {
    rating.value = 0 // toggle off → remove
    tags.value = []
  } else {
    rating.value = value
    tags.value = [] // reset reasons when flipping polarity
  }
  await syncFavorite()
  await submit()
}

async function toggleTag(tag: RatingTag): Promise<void> {
  tags.value = tags.value.includes(tag)
    ? tags.value.filter((t) => t !== tag)
    : [...tags.value, tag]
  await submit()
}
</script>

<template>
  <div class="rate" role="group" aria-label="Rate this pattern">
    <span class="rate__label">Rate</span>
    <div class="rate__thumbs">
      <button
        class="rate__btn"
        :class="{ 'rate__btn--up': rating === 1 }"
        type="button"
        :disabled="busy"
        :aria-pressed="rating === 1"
        :title="isAuthenticated ? 'Save + like' : 'Sign in to rate'"
        aria-label="Like and save to favorites"
        @click="setRating(1)"
      >
        👍
      </button>
      <button
        class="rate__btn"
        :class="{ 'rate__btn--down': rating === -1 }"
        type="button"
        :disabled="busy"
        :aria-pressed="rating === -1"
        :title="isAuthenticated ? 'Bad pattern' : 'Sign in to rate'"
        @click="setRating(-1)"
      >
        👎
      </button>
    </div>

    <span v-if="rating === 1 && savedId" class="rate__saved">★ saved to favorites</span>
    <span v-else class="rate__hint">saves to your favorites</span>

    <div v-if="rating !== 0" class="rate__reasons">
      <button
        v-for="tag in rating === -1 ? DISLIKE_TAGS : LIKE_TAGS"
        :key="tag"
        class="rate__chip"
        :class="{ 'rate__chip--on': tags.includes(tag) }"
        type="button"
        :aria-pressed="tags.includes(tag)"
        @click="toggleTag(tag)"
      >
        {{ tag.replace(/_/g, ' ') }}
      </button>
      <input
        v-model="note"
        class="rate__note"
        type="text"
        maxlength="500"
        placeholder="note (optional)"
        aria-label="Optional rating note"
        @blur="submit"
      />
    </div>
  </div>
</template>

<style scoped>
.rate {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: var(--r-md); border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
}
.rate__label {
  font-family: var(--font-mono); font-size: 0.6rem; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--text-faint);
}
.rate__thumbs { display: flex; gap: 8px; }
.rate__btn {
  min-width: 42px; padding: 5px 12px; border-radius: var(--r-sm); border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--panel));
  font-size: 1.05rem; line-height: 1; cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.18s ease;
}
.rate__btn:hover:not(:disabled) { box-shadow: inset 0 0 0 1px rgba(255, 157, 60, 0.28); }
.rate__btn--up {
  border-color: var(--amber-dim);
  box-shadow: inset 0 0 0 1px var(--amber-dim), 0 0 12px -4px var(--amber-glow);
}
.rate__btn--down { border-color: var(--danger); box-shadow: inset 0 0 0 1px var(--danger); }
.rate__btn:disabled { opacity: 0.55; cursor: not-allowed; }
.rate__saved { font-family: var(--font-mono); font-size: 0.62rem; color: var(--amber-bright); }
.rate__hint { font-family: var(--font-mono); font-size: 0.62rem; color: var(--text-faint); }
.rate__reasons {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px; flex-basis: 100%; margin-top: 2px;
}
.rate__chip {
  padding: 3px 8px; border-radius: var(--r-sm); border: 1px dashed var(--edge);
  background: transparent; color: var(--text-dim); font-family: var(--font-mono);
  font-size: 0.64rem; cursor: pointer;
}
.rate__chip--on { color: var(--amber-bright); border-style: solid; border-color: var(--amber-dim); }
.rate__note {
  flex: 1 1 140px; min-width: 120px; padding: 4px 8px; border-radius: var(--r-sm);
  border: 1px solid var(--edge); background: var(--field-ink); color: var(--text); font-size: 0.72rem;
}
</style>
