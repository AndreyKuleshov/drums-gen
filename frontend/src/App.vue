<script setup lang="ts">
import { ref } from 'vue'

import GenerationForm from './components/GenerationForm.vue'
import PlayerControls from './components/PlayerControls.vue'
import ScoreView from './components/ScoreView.vue'
import type { Phrase } from './types'

const phrase = ref<Phrase | null>(null)
</script>

<template>
  <main>
    <h1>Drum Pattern Generator</h1>
    <GenerationForm @update:phrase="phrase = $event" />
    <ScoreView :phrase="phrase" />
    <PlayerControls :phrase="phrase" />
  </main>
</template>
