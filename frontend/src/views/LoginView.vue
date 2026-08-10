<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import AuthCard from '../components/AuthCard.vue'
import PasswordField from '../components/PasswordField.vue'
import { ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'

const route = useRoute()
const router = useRouter()
const { login } = useAuth()

const next = typeof route.query.next === 'string' ? route.query.next : '/account'
// Context when bounced here from a gated action (e.g. saving a pattern).
const subtitle =
  route.query.reason === 'save'
    ? 'Sign in to save that pattern to your favorites.'
    : 'Welcome back to the rudiment engine.'

const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit(): Promise<void> {
  error.value = ''
  busy.value = true
  try {
    await login(email.value.trim(), password.value)
    await router.push(next)
  } catch (err) {
    if (err instanceof ApiError && err.status === 403) {
      error.value = 'Please confirm your email first — check your inbox for the link.'
    } else if (err instanceof ApiError && err.status === 401) {
      error.value = 'Invalid email or password.'
    } else {
      error.value = 'Something went wrong. Please try again.'
    }
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard title="Sign in" :subtitle="subtitle">
    <form class="authform" @submit.prevent="submit">
      <p v-if="error" class="formmsg formmsg--error" role="alert">{{ error }}</p>

      <div class="field">
        <label class="field__label" for="email">Email</label>
        <input
          id="email"
          v-model="email"
          class="field__input"
          type="email"
          autocomplete="email"
          placeholder="you@example.com"
          required
        />
      </div>

      <PasswordField
        id="password"
        v-model="password"
        label="Password"
        autocomplete="current-password"
      />

      <button class="btn-primary" type="submit" :disabled="busy">
        {{ busy ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>

    <p class="authfoot">
      <RouterLink to="/forgot" class="authlink">Forgot password?</RouterLink>
    </p>
    <p class="authfoot">
      No account? <RouterLink to="/register" class="authlink">Create one</RouterLink>
    </p>
  </AuthCard>
</template>
