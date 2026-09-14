<script setup lang="ts">
import { computed } from 'vue'

import { socialIcon } from '../lib/social'

const props = defineProps<{ url: string; size?: number }>()
const icon = computed(() => socialIcon(props.url))
</script>

<template>
  <svg
    v-if="icon"
    :width="size ?? 18"
    :height="size ?? 18"
    viewBox="0 0 24 24"
    role="img"
    :aria-label="icon.label"
  >
    <path :d="icon.path" fill="currentColor" />
  </svg>
</template>
