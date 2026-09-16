<script setup lang="ts">
import { onMounted, ref } from 'vue'

import RatingPreviewModal from '../components/RatingPreviewModal.vue'
import { adminListRatings, adminModerate, type AdminRating, type RatingSummary } from '../lib/ratings'

const items = ref<AdminRating[]>([])
const total = ref(0)
const summary = ref<RatingSummary | null>(null)
const loading = ref(true)
const error = ref('')
const includeModerated = ref(false)
const preview = ref<AdminRating | null>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const page = await adminListRatings({ includeModerated: includeModerated.value })
    items.value = page.items
    total.value = page.total
    summary.value = page.summary
  } catch {
    error.value = 'Could not load ratings.'
  } finally {
    loading.value = false
  }
}

async function remove(row: AdminRating): Promise<void> {
  await adminModerate(row.id, true)
  await load()
}

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
      <span class="ratesum__stat">👍 <b>{{ summary.likes }}</b></span>
      <span class="ratesum__stat">👎 <b>{{ summary.dislikes }}</b></span>
      <span v-for="tc in summary.top_dislike_tags" :key="tc.tag" class="ratesum__tag">
        {{ tc.tag.replace(/_/g, ' ') }} · {{ tc.count }}
      </span>
    </section>

    <label class="ratefilter">
      <input v-model="includeModerated" type="checkbox" @change="load" />
      show moderated
    </label>

    <p v-if="loading" class="muted">Loading…</p>
    <p v-else-if="error" class="muted" role="alert">{{ error }}</p>
    <p v-else-if="items.length === 0" class="muted">No ratings yet.</p>

    <div v-else class="ratetable-wrap">
      <table class="ratetable">
        <thead>
          <tr>
            <th>Rating</th><th>Tags</th><th>Note</th><th>Kind</th>
            <th>Params</th><th>Ver</th><th>Rater</th><th>When</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id" :class="{ 'is-out': row.moderated_out }">
            <td>{{ row.rating > 0 ? '👍' : '👎' }}</td>
            <td>{{ row.tags.join(', ') }}</td>
            <td>{{ row.note }}</td>
            <td>{{ row.kind }}</td>
            <td class="ratetable__params">{{ paramSummary(row.params) }}</td>
            <td>{{ row.generator_version }}</td>
            <td>{{ row.rater_email }}</td>
            <td>{{ new Date(row.created_at).toLocaleString() }}</td>
            <td class="ratetable__actions">
              <button type="button" class="ratebtn" @click="preview = row">View</button>
              <button
                v-if="!row.moderated_out"
                type="button"
                class="ratebtn ratebtn--danger"
                @click="remove(row)"
              >
                Remove
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <RatingPreviewModal
      v-if="preview"
      :kind="preview.kind"
      :pattern="preview.pattern"
      :tempo="Number((preview.params as Record<string, unknown>).tempo_bpm) || undefined"
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
.ratefilter { font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-dim); display: inline-flex; gap: 6px; align-items: center; }
.ratetable-wrap { overflow-x: auto; }
.ratetable { width: 100%; border-collapse: collapse; font-size: 0.72rem; }
.ratetable th, .ratetable td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--edge); vertical-align: top; }
.ratetable__params { font-family: var(--font-mono); white-space: nowrap; }
.ratetable__actions { display: flex; gap: 6px; }
.ratetable tr.is-out { opacity: 0.5; }
.ratebtn {
  padding: 5px 10px; border-radius: var(--r-sm); border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel)); color: var(--text-dim);
  font-family: var(--font-mono); font-size: 0.62rem; cursor: pointer;
}
.ratebtn:hover { color: var(--amber-bright); }
.ratebtn--danger:hover { color: var(--danger); }
</style>
