<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import AuthCard from '../components/AuthCard.vue'
import { useAuth } from '../lib/auth'

const { register } = useAuth()

const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)
const done = ref(false)

async function submit(): Promise<void> {
  error.value = ''
  if (password.value.length < 8) {
    error.value = 'Password must be at least 8 characters.'
    return
  }
  busy.value = true
  try {
    await register(email.value.trim(), password.value, name.value.trim())
    done.value = true
  } catch {
    error.value = 'Something went wrong. Please try again.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard
    v-if="!done"
    title="Create account"
    subtitle="Save the patterns you like and build your own kit of favorites."
  >
    <form class="authform" @submit.prevent="submit">
      <p v-if="error" class="formmsg formmsg--error" role="alert">{{ error }}</p>

      <div class="field">
        <label class="field__label" for="name">Display name</label>
        <input
          id="name"
          v-model="name"
          class="field__input"
          type="text"
          autocomplete="nickname"
          maxlength="80"
          required
        />
      </div>

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

      <div class="field">
        <label class="field__label" for="password">Password</label>
        <input
          id="password"
          v-model="password"
          class="field__input"
          type="password"
          autocomplete="new-password"
          minlength="8"
          required
        />
      </div>

      <button class="btn-primary" type="submit" :disabled="busy">
        {{ busy ? 'Creating…' : 'Create account' }}
      </button>
    </form>

    <p class="authfoot">
      Already have an account? <RouterLink to="/login" class="authlink">Sign in</RouterLink>
    </p>
  </AuthCard>

  <AuthCard v-else title="Check your inbox" subtitle="One more step to activate your account.">
    <p class="formmsg formmsg--ok">
      We sent a confirmation link to <strong>{{ email }}</strong>. Click it to verify your
      email and finish signing up.
    </p>
    <p class="authfoot">
      Didn't get it? Check spam, or
      <RouterLink to="/register" class="authlink" @click="done = false">try again</RouterLink>.
    </p>
  </AuthCard>
</template>
