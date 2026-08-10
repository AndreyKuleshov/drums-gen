<script setup lang="ts">
import { ref } from 'vue'

withDefaults(
  defineProps<{
    id: string
    label: string
    modelValue: string
    autocomplete?: string
    hint?: string
    minlength?: number
  }>(),
  { autocomplete: 'current-password', hint: undefined, minlength: undefined },
)
defineEmits<{ 'update:modelValue': [string] }>()

const show = ref(false)
</script>

<template>
  <div class="field">
    <label class="field__label" :for="id">{{ label }}</label>
    <div class="field__control">
      <input
        :id="id"
        class="field__input"
        :type="show ? 'text' : 'password'"
        :autocomplete="autocomplete"
        :minlength="minlength"
        :value="modelValue"
        required
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <button
        class="field__reveal"
        type="button"
        :aria-pressed="show"
        :aria-label="show ? 'Hide password' : 'Show password'"
        @click="show = !show"
      >
        {{ show ? 'Hide' : 'Show' }}
      </button>
    </div>
    <p v-if="hint" class="field__hint">{{ hint }}</p>
  </div>
</template>
