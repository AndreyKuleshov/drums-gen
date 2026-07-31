<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import AuthCard from '../components/AuthCard.vue'
import { ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'

const route = useRoute()
const router = useRouter()
const { reset } = useAuth()

const password = ref('')
const error = ref('')
const busy = ref(false)
const done = ref(false)

const token = typeof route.query.token === 'string' ? route.query.token : ''

async function submit(): Promise<void> {
  error.value = ''
  if (password.value.length < 8) {
    error.value = 'Password must be at least 8 characters.'
    return
  }
  busy.value = true
  try {
    await reset(token, password.value)
    done.value = true
    setTimeout(() => router.push('/login'), 1600)
  } catch (err) {
    // The backend returns 400 both for a bad token and a reused password; show
    // its (user-friendly) message so the reason is clear.
    error.value =
      err instanceof ApiError && err.status === 400
        ? err.message
        : 'Something went wrong. Please try again.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard v-if="!token" title="Reset password">
    <p class="formmsg formmsg--error" role="alert">This reset link is missing its token.</p>
    <p class="authfoot">
      <RouterLink to="/forgot" class="authlink">Request a new link</RouterLink>
    </p>
  </AuthCard>

  <AuthCard v-else-if="!done" title="Set a new password">
    <form class="authform" @submit.prevent="submit">
      <p v-if="error" class="formmsg formmsg--error" role="alert">{{ error }}</p>
      <div class="field">
        <label class="field__label" for="password">New password</label>
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
        {{ busy ? 'Saving…' : 'Save password' }}
      </button>
    </form>
  </AuthCard>

  <AuthCard v-else title="Password updated">
    <p class="formmsg formmsg--ok">Your password has been reset. Redirecting to sign in…</p>
    <p class="authfoot"><RouterLink to="/login" class="authlink">Sign in now</RouterLink></p>
  </AuthCard>
</template>
