import { createRouter, createWebHistory } from 'vue-router'

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
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
