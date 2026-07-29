<script setup lang="ts">
import { playPhrase, stopPhrase } from '../lib/audio'
import type { Phrase } from '../types'

const props = defineProps<{ phrase: Phrase | null }>()

async function onPlay(): Promise<void> {
  if (props.phrase !== null) await playPhrase(props.phrase)
}
</script>

<template>
  <div>
    <button :disabled="phrase === null" @click="onPlay">Play</button>
    <button @click="stopPhrase">Stop</button>
  </div>
</template>
