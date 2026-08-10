<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import AuthCard from '../components/AuthCard.vue'
import PasswordField from '../components/PasswordField.vue'
import { useAuth } from '../lib/auth'

const { register } = useAuth()

const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)
const done = ref(false)
const resent = ref(false)

async function submit(): Promise<void> {
  error.value = ''
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

async function resend(): Promise<void> {
  // The backend re-issues a fresh verification link for an unverified account.
  resent.value = false
  await register(email.value.trim(), password.value, name.value.trim())
  resent.value = true
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
          placeholder="e.g. Buddy Rich"
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
          placeholder="you@example.com"
          required
        />
      </div>

      <PasswordField
        id="password"
        v-model="password"
        label="Password"
        autocomplete="new-password"
        :minlength="8"
        hint="At least 8 characters."
      />

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
    <p v-if="resent" class="formmsg formmsg--ok" role="status">Link re-sent — check again.</p>
    <p class="authfoot">
      Didn't get it? Check spam, or
      <button class="authlink authlink--btn" type="button" @click="resend">resend the link</button>.
    </p>
  </AuthCard>
</template>

<style scoped>
.authlink--btn {
  border: none;
  background: none;
  padding: 0;
  font: inherit;
  cursor: pointer;
}
</style>
