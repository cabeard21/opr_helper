import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import type { ServerOptions } from 'vite'

export function devServerHmrConfig(env: { VITE_DISABLE_HMR?: string } = process.env): ServerOptions['hmr'] {
  return env.VITE_DISABLE_HMR === '1' ? false : undefined
}

export function devServerProxyConfig(env: { BACKEND_ORIGIN?: string } = process.env): ServerOptions['proxy'] {
  return {
    '/api': {
      target: env.BACKEND_ORIGIN ?? 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    hmr: devServerHmrConfig(),
    proxy: devServerProxyConfig(),
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    globals: true,
  },
})
