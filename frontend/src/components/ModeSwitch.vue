<script setup lang="ts">
// The single distinguishing control between the two studio modes. No routing —
// it just flips a reactive mode on the one page.
const mode = defineModel<'groove' | 'exercise'>({ required: true })
const opts = [
  { value: 'groove', label: 'Pattern' },
  { value: 'exercise', label: 'Exercises' },
] as const
</script>

<template>
  <nav class="modeswitch" aria-label="Mode">
    <button
      v-for="o in opts"
      :key="o.value"
      type="button"
      class="modeswitch__opt"
      :class="{ 'modeswitch__opt--on': mode === o.value }"
      :aria-pressed="mode === o.value"
      @click="mode = o.value"
    >
      {{ o.label }}
    </button>
  </nav>
</template>

<style scoped>
.modeswitch {
  display: inline-flex;
  padding: 3px;
  gap: 2px;
  border-radius: 999px;
  border: 1px solid var(--edge);
  background: #100e0c;
  box-shadow: var(--inset);
}

.modeswitch__opt {
  padding: 6px 14px;
  border: none;
  border-radius: 999px;
  color: var(--text-dim);
  background: transparent;
  font-family: var(--font-mono);
  font-size: 0.64rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  cursor: pointer;
  transition:
    color 0.15s ease,
    background 0.15s ease;
}

.modeswitch__opt--on {
  color: #1a1206;
  background: linear-gradient(180deg, var(--amber), var(--amber-dim));
  box-shadow: 0 0 14px -4px var(--amber-glow);
}
</style>
