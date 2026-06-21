import { describe, expect, it } from 'vitest'

import { devServerHmrConfig } from './vite.config'

describe('Vite dev server config', () => {
  it('disables HMR when the mobile network launcher opts out', () => {
    expect(devServerHmrConfig({ VITE_DISABLE_HMR: '1' })).toBe(false)
  })

  it('keeps normal desktop dev HMR enabled by default', () => {
    expect(devServerHmrConfig({})).toBeUndefined()
  })
})
