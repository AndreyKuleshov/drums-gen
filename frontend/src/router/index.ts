import { createRouter, createWebHistory } from 'vue-router'

import { useAuth } from '../lib/auth'
import GeneratorView from '../views/GeneratorView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'generator', component: GeneratorView },
    {
      path: '/rudiments',
      name: 'rudiments',
      component: () => import('../views/RudimentsView.vue'),
    },
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
    { path: '/register', name: 'register', component: () => import('../views/RegisterView.vue') },
    { path: '/verify', name: 'verify', component: () => import('../views/VerifyView.vue') },
    { path: '/forgot', name: 'forgot', component: () => import('../views/ForgotView.vue') },
    { path: '/reset', name: 'reset', component: () => import('../views/ResetView.vue') },
    {
      path: '/account',
      name: 'account',
      component: () => import('../views/AccountView.vue'),
      meta: { requiresAuth: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

// Gate protected routes. Auth state is hydrated once at app start (main.ts);
// `ready` guarantees we don't bounce a signed-in user on a hard refresh.
router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) return true
  const { isAuthenticated, ready, refresh } = useAuth()
  if (!ready.value) await refresh()
  if (!isAuthenticated.value) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  return true
})
