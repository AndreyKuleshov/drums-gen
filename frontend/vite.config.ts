import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  // Same-origin in dev: proxy /api -> backend, stripping the prefix exactly like
  // nginx does in prod. This lets the session cookie flow without cross-origin.
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    globals: true,
    environment: 'node',
    server: { deps: { inline: ['tone'] } },
  },
})
