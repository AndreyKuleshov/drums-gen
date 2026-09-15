<script setup lang="ts">
defineProps<{ kind: 'exercise' | 'pattern'; pattern: unknown; tempo?: number }>()
defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <div />
</template>
