<script setup lang="ts">
import { reactive } from 'vue'

import type { Phrase } from '../types'

const emit = defineEmits<{ (e: 'update:phrase', phrase: Phrase): void }>()

const form = reactive({
  num: 4,
  den: 4,
  num_bars: 1,
  min_subdivision: '1/16',
  tempo_bpm: 100,
  accent_mode: 'rudiment',
})

const error = reactive({ message: '' })

async function submit(): Promise<void> {
  error.message = ''
  const resp = await fetch('http://localhost:8000/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      time_sig: { num: form.num, den: form.den },
      num_bars: form.num_bars,
      min_subdivision: form.min_subdivision,
      tempo_bpm: form.tempo_bpm,
      accent_mode: form.accent_mode,
    }),
  })
  if (!resp.ok) {
    error.message = `Generation failed (${resp.status})`
    return
  }
  emit('update:phrase', (await resp.json()) as Phrase)
}
</script>

<template>
  <form @submit.prevent="submit">
    <label>Beats <input v-model.number="form.num" type="number" min="1" /></label>
    <label>/ <input v-model.number="form.den" type="number" min="1" /></label>
    <label>Bars <input v-model.number="form.num_bars" type="number" min="1" /></label>
    <label>
      Subdivision
      <select v-model="form.min_subdivision">
        <option value="1/8">1/8</option>
        <option value="1/16">1/16</option>
        <option value="1/12">triplet 1/12</option>
      </select>
    </label>
    <label>Tempo <input v-model.number="form.tempo_bpm" type="number" min="20" /></label>
    <label>
      Accents
      <select v-model="form.accent_mode">
        <option value="rudiment">rudiment</option>
        <option value="metric">metric</option>
        <option value="both">both</option>
      </select>
    </label>
    <button type="submit">Generate</button>
    <p v-if="error.message" role="alert">{{ error.message }}</p>
  </form>
</template>
