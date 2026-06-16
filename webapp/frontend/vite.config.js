import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    tailwindcss(),
    svelte(),
  ],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        configure: (proxy) => {
          // Disable buffering so SSE (EventSource) streams through cleanly
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('accept-encoding', 'identity')
          })
        },
      },
    },
  },
  build: {
    outDir: 'dist',
  },
  test: {
    environment: 'node',
    include: ['src/tests/**/*.test.js'],
  },
})
