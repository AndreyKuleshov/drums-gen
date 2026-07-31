<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import AuthCard from '../components/AuthCard.vue'
import { useAuth } from '../lib/auth'

const { forgot } = useAuth()

const email = ref('')
const busy = ref(false)
const done = ref(false)

async function submit(): Promise<void> {
  busy.value = true
  try {
    await forgot(email.value.trim())
  } finally {
    // Always show the same confirmation — never reveal whether the email exists.
    busy.value = false
    done.value = true
  }
}
</script>

<template>
  <AuthCard
    v-if="!done"
    title="Reset password"
    subtitle="Enter your email and we'll send a reset link."
  >
    <form class="authform" @submit.prevent="submit">
      <div class="field">
        <label class="field__label" for="email">Email</label>
        <input
          id="email"
          v-model="email"
          class="field__input"
          type="email"
          autocomplete="email"
          required
        />
      </div>
      <button class="btn-primary" type="submit" :disabled="busy">
        {{ busy ? 'Sending…' : 'Send reset link' }}
      </button>
    </form>
    <p class="authfoot"><RouterLink to="/login" class="authlink">Back to sign in</RouterLink></p>
  </AuthCard>

  <AuthCard v-else title="Check your inbox">
    <p class="formmsg formmsg--ok">
      If an account exists for that email, a reset link is on its way. The link expires in a
      couple of hours.
    </p>
    <p class="authfoot"><RouterLink to="/login" class="authlink">Back to sign in</RouterLink></p>
  </AuthCard>
</template>
