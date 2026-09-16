<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
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

const DISLIKE_TAGS: RatingTag[] = [
  'too_busy',
  'boring',
  'unmusical',
  'awkward_sticking',
  'repetitive',
  'too_hard',
]

const rating = ref<0 | 1 | -1>(0)
const tags = ref<RatingTag[]>([])
const note = ref('')
const busy = ref(false)
const savedId = ref<string | null>(null)
const showToast = ref(false) // 👍 confirmation
const showForm = ref(false) // 👎 tags + comment popover
let toastTimer: ReturnType<typeof setTimeout> | null = null

// A new pattern is a new data point — reset. Any previously-saved favorite
// persists on its own; it's not tied to this control instance.
watch(
  () => props.pattern,
  () => {
    rating.value = 0
    tags.value = []
    note.value = ''
    savedId.value = null
    showForm.value = false
    showToast.value = false
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

// Save/unsave the favorite on the RATING VALUE transition only.
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

function flashToast(): void {
  showToast.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    showToast.value = false
  }, 2200)
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
  // 👍 → transient "added to favorites"; 👎 → open the tags/comment form.
  showForm.value = rating.value === -1
  if (rating.value === 1) flashToast()
  else showToast.value = false
}

async function toggleTag(tag: RatingTag): Promise<void> {
  tags.value = tags.value.includes(tag)
    ? tags.value.filter((t) => t !== tag)
    : [...tags.value, tag]
  await submit()
}

onBeforeUnmount(() => {
  if (toastTimer) clearTimeout(toastTimer)
})
</script>

<template>
  <div class="rate" role="group" aria-label="Rate this pattern">
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
        :title="isAuthenticated ? 'Dislike' : 'Sign in to rate'"
        @click="setRating(-1)"
      >
        👎
      </button>
    </div>

    <div v-if="showToast" class="rate__toast" role="status">★ Added to favorites</div>

    <div v-if="showForm" class="rate__form" role="group" aria-label="Why the dislike?">
      <div class="rate__form-head">
        <span>What's off?</span>
        <button type="button" class="rate__x" aria-label="Close" @click="showForm = false">×</button>
      </div>
      <div class="rate__chips">
        <button
          v-for="tag in DISLIKE_TAGS"
          :key="tag"
          class="rate__chip"
          :class="{ 'rate__chip--on': tags.includes(tag) }"
          type="button"
          :aria-pressed="tags.includes(tag)"
          @click="toggleTag(tag)"
        >
          {{ tag.replace(/_/g, ' ') }}
        </button>
      </div>
      <textarea
        v-model="note"
        class="rate__note"
        rows="2"
        maxlength="500"
        placeholder="comment (optional)"
        aria-label="Dislike comment"
        @blur="submit"
      />
      <button type="button" class="rate__done" @click="showForm = false">Done</button>
    </div>
  </div>
</template>

<style scoped>
.rate {
  position: relative;
}
.rate__thumbs {
  display: flex;
  gap: 6px;
}
.rate__btn {
  width: 40px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: var(--r-sm);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--panel));
  font-size: 1.05rem;
  line-height: 1;
  cursor: pointer;
  box-shadow: var(--shadow-1);
  transition:
    border-color 0.15s ease,
    box-shadow 0.18s ease;
}
.rate__btn:hover:not(:disabled) {
  box-shadow: inset 0 0 0 1px rgba(255, 157, 60, 0.3);
}
.rate__btn--up {
  border-color: var(--amber-dim);
  box-shadow: inset 0 0 0 1px var(--amber-dim), 0 0 12px -4px var(--amber-glow);
}
.rate__btn--down {
  border-color: var(--danger);
  box-shadow: inset 0 0 0 1px var(--danger);
}
.rate__btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.rate__toast {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  white-space: nowrap;
  padding: 6px 10px;
  border-radius: var(--r-sm);
  border: 1px solid var(--amber-dim);
  background: #0b0908;
  color: var(--amber-bright);
  font-family: var(--font-mono);
  font-size: 0.64rem;
  box-shadow: var(--shadow-2);
  z-index: 5;
}
.rate__form {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 260px;
  z-index: 6;
  padding: 10px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised-hi), var(--panel));
  box-shadow: var(--shadow-3);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.rate__form-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint);
}
.rate__x {
  border: none;
  background: transparent;
  color: var(--text-faint);
  font-size: 1.05rem;
  line-height: 1;
  cursor: pointer;
}
.rate__x:hover {
  color: var(--danger);
}
.rate__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.rate__chip {
  padding: 3px 8px;
  border-radius: var(--r-sm);
  border: 1px dashed var(--edge);
  background: transparent;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  cursor: pointer;
}
.rate__chip--on {
  color: var(--amber-bright);
  border-style: solid;
  border-color: var(--amber-dim);
}
.rate__note {
  padding: 6px 8px;
  border-radius: var(--r-sm);
  border: 1px solid var(--edge);
  background: var(--field-ink);
  color: var(--text);
  font-family: inherit;
  font-size: 0.72rem;
  resize: vertical;
}
.rate__done {
  align-self: flex-end;
  padding: 4px 12px;
  border-radius: var(--r-sm);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.62rem;
  cursor: pointer;
}
.rate__done:hover {
  color: var(--amber-bright);
}
</style>
