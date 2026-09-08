<script setup lang="ts">
const props = defineProps<{
  modelValue: number
  min: number
  max: number
  step?: number
  label: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', value: number): void }>()

const clamp = (n: number): number => Math.min(props.max, Math.max(props.min, n))

function bump(dir: number): void {
  emit('update:modelValue', clamp(props.modelValue + dir * (props.step ?? 1)))
}

// While typing, only cap the MAX; the min-clamp is deferred to blur. Otherwise a
// value whose leading digits are below the min (e.g. "1" on the way to "150")
// snaps up to the min on the first keystroke, making it impossible to type.
function onInput(event: Event): void {
  const el = event.target as HTMLInputElement
  if (el.value === '') return // allow an empty field mid-edit; blur will settle it
  const raw = Number(el.value)
  if (!Number.isNaN(raw)) emit('update:modelValue', Math.min(props.max, raw))
}

// Settle the field when it loses focus: clamp to [min, max] and reflect the
// clamped value even if the model didn't change.
function onBlur(event: Event): void {
  const el = event.target as HTMLInputElement
  const raw = Number(el.value)
  const value = clamp(el.value === '' || Number.isNaN(raw) ? props.min : raw)
  emit('update:modelValue', value)
  el.value = String(value)
}
</script>

<template>
  <div class="stepper">
    <button
      type="button"
      class="stepper__key"
      :disabled="modelValue <= min"
      :aria-label="`Decrease ${label}`"
      @click="bump(-1)"
    >
      &minus;
    </button>
    <input
      class="stepper__value"
      type="number"
      inputmode="numeric"
      :value="modelValue"
      :min="min"
      :max="max"
      :aria-label="label"
      @input="onInput"
      @blur="onBlur"
    />
    <button
      type="button"
      class="stepper__key"
      :disabled="modelValue >= max"
      :aria-label="`Increase ${label}`"
      @click="bump(1)"
    >
      +
    </button>
  </div>
</template>

<style scoped>
.stepper {
  display: inline-flex;
  align-items: stretch;
  background: #100e0c;
  border: 1px solid var(--edge);
  border-radius: var(--r-md);
  box-shadow: var(--inset);
  overflow: hidden;
}

.stepper__key {
  width: 34px;
  display: grid;
  place-items: center;
  background: linear-gradient(180deg, var(--raised-hi), var(--raised));
  border: none;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 1.15rem;
  line-height: 1;
  transition:
    color 0.15s ease,
    filter 0.12s ease,
    transform 0.1s ease;
}

.stepper__key:first-child {
  border-right: 1px solid var(--edge);
}

.stepper__key:last-child {
  border-left: 1px solid var(--edge);
}

.stepper__key:hover:not(:disabled) {
  color: var(--amber-bright);
}

.stepper__key:active:not(:disabled) {
  transform: translateY(1px);
  filter: brightness(1.1);
}

.stepper__key:disabled {
  color: var(--text-faint);
  opacity: 0.4;
}

.stepper__value {
  width: 52px;
  padding: 10px 4px;
  border: none;
  background: transparent;
  font-family: var(--font-mono);
  font-size: 1.05rem;
  font-weight: 500;
  color: var(--amber-bright);
  text-align: center;
  -moz-appearance: textfield;
  appearance: textfield;
}

.stepper__value::-webkit-outer-spin-button,
.stepper__value::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
