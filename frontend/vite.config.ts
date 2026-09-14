import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  // Same-origin in dev: proxy /api -> backend, stripping the prefix exactly like
  // nginx does in prod. This lets the session cookie flow without cross-origin.
  // Target 127.0.0.1 (not `localhost`) so the proxy can't resolve to an IPv6
  // listener from an unrelated container that happens to publish port 8000.
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
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
