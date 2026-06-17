import axios from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from './client'

vi.mock('axios', () => ({
  default: {
    create: vi.fn(),
  },
}))

const getRequest = vi.fn()
const postRequest = vi.fn()

afterEach(() => {
  getRequest.mockReset()
  postRequest.mockReset()
  vi.mocked(axios.create).mockReset()
})

describe('apiClient', () => {
  it('unwraps successful API envelopes', async () => {
    vi.mocked(axios.create).mockReturnValue({ get: getRequest } as never)
    getRequest.mockResolvedValue({ data: { data: [{ id: 1, name: 'Kingdom' }], error: null } })

    const factions = await apiClient.getFactions()

    expect(factions).toEqual([{ id: 1, name: 'Kingdom' }])
    expect(getRequest).toHaveBeenCalledWith('/factions/')
  })

  it('throws the envelope error for failed responses', async () => {
    vi.mocked(axios.create).mockReturnValue({ get: getRequest } as never)
    getRequest.mockResolvedValue({ data: { data: null, error: 'Faction not found.' } })

    await expect(apiClient.getFactionUnits(99)).rejects.toThrow('Faction not found.')
  })

  it('posts calculation requests and unwraps successful results', async () => {
    vi.mocked(axios.create).mockReturnValue({ post: postRequest } as never)
    postRequest.mockResolvedValue({
      data: {
        data: {
          ev: 1.25,
          distribution: [{ wounds: 0, probability: 0.25 }],
          p_zero_wounds: 0.25,
          p_kill_model: 0.75,
          p_kill_unit: 0.5,
        },
        error: null,
      },
    })

    const result = await apiClient.calculateEv({
      unit_id: 10,
      weapon_id: 30,
      target: { defense: 4, tough: 3 },
      modifiers: { stealth: true, indirect: false },
    })

    expect(result.ev).toBe(1.25)
    expect(postRequest).toHaveBeenCalledWith('/calc/ev/', {
      unit_id: 10,
      weapon_id: 30,
      target: { defense: 4, tough: 3 },
      modifiers: { stealth: true, indirect: false },
    })
  })
})
