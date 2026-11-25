import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

const runnerDir = fileURLToPath(new URL('../runner', import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@runner': runnerDir } },
  server: {
    port: 5173,
    fs: { allow: ['..'] },
    proxy: { '/api': { target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000', changeOrigin: true } },
  },
  worker: { format: 'es' },
  build: {
    chunkSizeWarningLimit: 4000,
  },
})
