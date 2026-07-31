<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import AuthCard from '../components/AuthCard.vue'
import { useAuth } from '../lib/auth'

const route = useRoute()
const router = useRouter()
const { verify } = useAuth()

const state = ref<'working' | 'ok' | 'error'>('working')

onMounted(async () => {
  const token = route.query.token
  if (typeof token !== 'string' || token.length === 0) {
    state.value = 'error'
    return
  }
  try {
    await verify(token)
    state.value = 'ok'
    setTimeout(() => router.push('/account'), 1400)
  } catch {
    state.value = 'error'
  }
})
</script>

<template>
  <AuthCard title="Confirming email">
    <p v-if="state === 'working'" class="formmsg" style="color: var(--text-dim)">
      Verifying your link…
    </p>

    <template v-else-if="state === 'ok'">
      <p class="formmsg formmsg--ok">
        Email confirmed — you're signed in. Taking you to your account…
      </p>
      <p class="authfoot"><RouterLink to="/account" class="authlink">Go now</RouterLink></p>
    </template>

    <template v-else>
      <p class="formmsg formmsg--error" role="alert">
        This confirmation link is invalid or has expired.
      </p>
      <p class="authfoot">
        <RouterLink to="/register" class="authlink">Register again</RouterLink> to get a fresh
        link.
      </p>
    </template>
  </AuthCard>
</template>
