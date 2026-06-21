import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import type { ServerOptions } from 'vite'

export function devServerHmrConfig(env: { VITE_DISABLE_HMR?: string } = process.env): ServerOptions['hmr'] {
  return env.VITE_DISABLE_HMR === '1' ? false : undefined
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    hmr: devServerHmrConfig(),
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    globals: true,
  },
})
