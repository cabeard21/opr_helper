import { describe, expect, it } from 'vitest'

import { devServerHmrConfig, devServerProxyConfig } from './vite.config'

describe('Vite dev server config', () => {
  it('disables HMR when the mobile network launcher opts out', () => {
    expect(devServerHmrConfig({ VITE_DISABLE_HMR: '1' })).toBe(false)
  })

  it('keeps normal desktop dev HMR enabled by default', () => {
    expect(devServerHmrConfig({})).toBeUndefined()
  })

  it('proxies API requests to the local backend by default', () => {
    expect(devServerProxyConfig({})).toEqual({
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    })
  })

  it('allows the backend proxy origin to be overridden', () => {
    expect(devServerProxyConfig({ BACKEND_ORIGIN: 'http://10.0.0.5:8000' })).toEqual({
      '/api': {
        target: 'http://10.0.0.5:8000',
        changeOrigin: true,
      },
    })
  })
})
