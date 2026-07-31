import './styles/theme.css'

import { createApp } from 'vue'

import App from './App.vue'
import { useAuth } from './lib/auth'
import { router } from './router'

// Hydrate auth from the session cookie before mounting so the header and route
// guards see the correct state on first paint (and on hard refresh).
useAuth()
  .refresh()
  .finally(() => {
    createApp(App).use(router).mount('#app')
  })
