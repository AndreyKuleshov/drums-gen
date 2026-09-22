<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import RatingPreviewModal from '../components/RatingPreviewModal.vue'
import ThumbIcon from '../components/ThumbIcon.vue'
import { adminListRatings, adminModerate, type AdminRating, type RatingSummary } from '../lib/ratings'

const PAGE = 25
const ALL_TAGS = [
  'too_busy', 'boring', 'unmusical', 'awkward_sticking', 'repetitive', 'too_hard',
  'groovy', 'creative', 'playable',
]

const items = ref<AdminRating[]>([])
const total = ref(0)
const summary = ref<RatingSummary | null>(null)
const loading = ref(true)
const error = ref('')
const includeModerated = ref(false)
const ratingFilter = ref<'' | '1' | '-1'>('')
const tagFilter = ref('')
const offset = ref(0)
const preview = ref<AdminRating | null>(null)
const confirmingId = ref<string | null>(null)
const busyId = ref<string | null>(null)

type SortKey = 'rating' | 'created_at' | 'rater_email'
const sortKey = ref<SortKey>('created_at')
const sortDir = ref<1 | -1>(-1)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const page = await adminListRatings({
      includeModerated: includeModerated.value,
      rating: ratingFilter.value ? Number(ratingFilter.value) : undefined,
      tag: tagFilter.value || undefined,
      limit: PAGE,
      offset: offset.value,
    })
    items.value = page.items
    total.value = page.total
    summary.value = page.summary
  } catch {
    error.value = 'Could not load ratings.'
  } finally {
    loading.value = false
  }
}

function applyFilters(): void {
  offset.value = 0
  confirmingId.value = null
  load()
}

const sorted = computed(() => {
  const arr = [...items.value]
  arr.sort((a, b) => {
    const av = String(a[sortKey.value] ?? '')
    const bv = String(b[sortKey.value] ?? '')
    return av < bv ? -sortDir.value : av > bv ? sortDir.value : 0
  })
  return arr
})

function toggleSort(key: SortKey): void {
  if (sortKey.value === key) sortDir.value = sortDir.value === 1 ? -1 : 1
  else {
    sortKey.value = key
    sortDir.value = 1
  }
}

async function moderate(row: AdminRating, out: boolean): Promise<void> {
  busyId.value = row.id
  confirmingId.value = null
  try {
    await adminModerate(row.id, out)
    await load()
  } finally {
    busyId.value = null
  }
}

function prev(): void {
  offset.value = Math.max(0, offset.value - PAGE)
  load()
}
function next(): void {
  if (offset.value + PAGE < total.value) {
    offset.value += PAGE
    load()
  }
}
const pageLabel = computed(() =>
  total.value === 0
    ? '0'
    : `${offset.value + 1}–${Math.min(offset.value + items.value.length, total.value)} of ${total.value}`,
)

function paramSummary(p: Record<string, unknown>): string {
  const fams = ['singles', 'odd', 'paradiddle'].filter((f) => p[f]).join('/')
  const grid = p.mixed ? 'mixed' : String(p.subdivision)
  return `${String(p.voicing)} · ${grid} · ${String(p.tempo_bpm)}bpm · ${String(p.num_bars)}b · ${fams}`
}

onMounted(load)
</script>

<template>
  <section>
    <section v-if="summary" class="ratesum">
      <span class="ratesum__stat">Total <b>{{ summary.total }}</b></span>
      <span class="ratesum__stat">
        <ThumbIcon dir="up" :size="15" class="thumb--like" /> <b>{{ summary.likes }}</b>
      </span>
      <span class="ratesum__stat">
        <ThumbIcon dir="down" :size="15" class="thumb--dislike" /> <b>{{ summary.dislikes }}</b>
      </span>
      <span v-for="tc in summary.top_dislike_tags" :key="tc.tag" class="ratesum__tag">
        {{ tc.tag.replace(/_/g, ' ') }} · {{ tc.count }}
      </span>
    </section>

    <div class="ratefilters">
      <label class="ratefilter">
        rating
        <select v-model="ratingFilter" data-test="rating-filter" @change="applyFilters">
          <option value="">all</option>
          <option value="1">like</option>
          <option value="-1">dislike</option>
        </select>
      </label>
      <label class="ratefilter">
        tag
        <select v-model="tagFilter" @change="applyFilters">
          <option value="">all</option>
          <option v-for="t in ALL_TAGS" :key="t" :value="t">{{ t.replace(/_/g, ' ') }}</option>
        </select>
      </label>
      <label class="ratefilter">
        <input v-model="includeModerated" type="checkbox" @change="applyFilters" />
        show moderated
      </label>
    </div>

    <p v-if="loading" class="ratemsg">Loading…</p>
    <p v-else-if="error" class="ratemsg" role="alert">{{ error }}</p>
    <p v-else-if="items.length === 0" class="ratemsg">No ratings match.</p>

    <template v-else>
      <div class="ratetable-wrap">
        <table class="ratetable">
          <thead>
            <tr>
              <th class="is-sortable" @click="toggleSort('rating')">Rating</th>
              <th>Tags</th><th>Note</th><th>Kind</th><th>Params</th><th>Ver</th>
              <th class="is-sortable" @click="toggleSort('rater_email')">Rater</th>
              <th class="is-sortable" @click="toggleSort('created_at')">When</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sorted" :key="row.id" :class="{ 'is-out': row.moderated_out }">
              <td>
                <ThumbIcon
                  :dir="row.rating > 0 ? 'up' : 'down'"
                  :size="18"
                  :class="row.rating > 0 ? 'thumb--like' : 'thumb--dislike'"
                />
                <span v-if="row.moderated_out" class="ratetag-out">removed</span>
              </td>
              <td>{{ row.tags.join(', ') }}</td>
              <td>{{ row.note }}</td>
              <td>Pattern 2.0</td>
              <td class="ratetable__params">{{ paramSummary(row.params) }}</td>
              <td class="ratetable__nowrap">{{ row.generator_version }}</td>
              <td>{{ row.rater_email }}</td>
              <td class="ratetable__nowrap">{{ new Date(row.created_at).toLocaleString() }}</td>
              <td class="ratetable__actions">
                <div class="ratetable__actions-row">
                <button type="button" class="ratebtn" :disabled="busyId === row.id" @click="preview = row">
                  View
                </button>
                <template v-if="confirmingId === row.id">
                  <button type="button" class="ratebtn ratebtn--confirm" @click="moderate(row, true)">
                    Confirm
                  </button>
                  <button type="button" class="ratebtn" @click="confirmingId = null">Cancel</button>
                </template>
                <button
                  v-else-if="!row.moderated_out"
                  type="button"
                  class="ratebtn ratebtn--danger"
                  :disabled="busyId === row.id"
                  @click="confirmingId = row.id"
                >
                  Remove
                </button>
                <button
                  v-else
                  type="button"
                  class="ratebtn"
                  :disabled="busyId === row.id"
                  @click="moderate(row, false)"
                >
                  Restore
                </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="ratepage">
        <button type="button" class="ratebtn" :disabled="offset === 0" @click="prev">‹ Prev</button>
        <span class="ratepage__label">{{ pageLabel }}</span>
        <button
          type="button"
          class="ratebtn"
          :disabled="offset + PAGE >= total"
          @click="next"
        >
          Next ›
        </button>
      </div>
    </template>

    <RatingPreviewModal
      v-if="preview"
      :kind="preview.kind"
      :pattern="preview.pattern"
      :tempo="Number((preview.params as Record<string, unknown>).tempo_bpm) || undefined"
      :ver="preview.generator_version"
      :rater="preview.rater_email"
      @close="preview = null"
    />
  </section>
</template>

<style scoped>
.ratesum { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.ratesum__stat { font-family: var(--font-mono); font-size: 0.8rem; color: var(--text); }
.ratesum__tag {
  font-family: var(--font-mono); font-size: 0.64rem; color: var(--text-dim);
  border: 1px solid var(--edge); border-radius: var(--r-sm); padding: 2px 7px;
}
.ratefilters { display: flex; flex-wrap: wrap; gap: 14px; align-items: center; margin: 10px 0; }
.ratefilter {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-dim);
}
.ratefilter select {
  padding: 3px 6px; border-radius: var(--r-sm); border: 1px solid var(--edge);
  background: var(--field-ink); color: var(--text); font-family: var(--font-mono); font-size: 0.7rem;
}
.ratemsg { color: var(--text-dim); font-size: 0.9rem; }
.ratetable-wrap { overflow-x: auto; }
.ratetable { width: 100%; border-collapse: collapse; font-size: 0.72rem; }
.ratetable th, .ratetable td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--edge); vertical-align: top; }
.ratetable th.is-sortable { cursor: pointer; user-select: none; }
.ratetable th.is-sortable:hover { color: var(--amber-bright); }
.ratetable__params { font-family: var(--font-mono); white-space: nowrap; }
.ratetable__nowrap { white-space: nowrap; }
/* Keep the cell a real table-cell (stretches to the row height so its
   border-bottom lines up); flex the buttons in an inner row instead. */
.ratetable__actions { white-space: nowrap; }
.ratetable__actions-row { display: flex; gap: 6px; }
.thumb--like { color: var(--amber-bright); }
.thumb--dislike { color: var(--text-dim); }
.ratetable tr.is-out { opacity: 0.55; }
.ratetag-out {
  font-family: var(--font-mono); font-size: 0.56rem; color: var(--danger);
  border: 1px solid var(--edge); border-radius: var(--r-sm); padding: 0 4px; margin-left: 4px;
}
.ratepage { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
.ratepage__label { font-family: var(--font-mono); font-size: 0.68rem; color: var(--text-dim); }
.ratebtn {
  padding: 5px 10px; border-radius: var(--r-sm); border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel)); color: var(--text-dim);
  font-family: var(--font-mono); font-size: 0.62rem; cursor: pointer;
}
.ratebtn:hover:not(:disabled) { color: var(--amber-bright); }
.ratebtn:disabled { opacity: 0.5; cursor: not-allowed; }
.ratebtn--danger:hover:not(:disabled) { color: var(--danger); }
.ratebtn--confirm { color: var(--danger); border-color: var(--danger); }
</style>
