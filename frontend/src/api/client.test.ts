import axios from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from './client'

vi.mock('axios', () => ({
  default: {
    create: vi.fn(),
    isAxiosError: vi.fn(),
  },
}))

const getRequest = vi.fn()
const postRequest = vi.fn()

afterEach(() => {
  getRequest.mockReset()
  postRequest.mockReset()
  vi.mocked(axios.create).mockReset()
  vi.mocked(axios.isAxiosError).mockReset()
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

  it('throws envelope errors from non-2xx Axios responses', async () => {
    const error = {
      response: {
        data: {
          data: null,
          error: 'Army Forge export requires native upgrade IDs. Re-sync army books before exporting.',
        },
      },
    }
    vi.mocked(axios.create).mockReturnValue({ get: getRequest } as never)
    vi.mocked(axios.isAxiosError).mockReturnValue(true)
    getRequest.mockRejectedValue(error)

    await expect(apiClient.exportArmyForgeList(1)).rejects.toThrow('Re-sync army books')
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

  it('posts list analysis requests and unwraps successful results', async () => {
    vi.mocked(axios.create).mockReturnValue({ post: postRequest } as never)
    postRequest.mockResolvedValue({
      data: {
        data: {
          list_id: 1,
          targets: [{ id: 'infantry', name: 'Infantry', defense: 5, tough: 1 }],
          units: [],
          totals: [{ target_id: 'infantry', ev: 0, wounds_per_100_points: 0 }],
        },
        error: null,
      },
    })

    const targets = [{ id: 'infantry', name: 'Infantry', defense: 5, tough: 1 }]
    const result = await apiClient.analyzeList(1, targets)

    expect(result.list_id).toBe(1)
    expect(postRequest).toHaveBeenCalledWith('/lists/1/analysis/', { targets })
  })

  it('posts advisor suggestion requests and unwraps successful results', async () => {
    vi.mocked(axios.create).mockReturnValue({ post: postRequest } as never)
    postRequest.mockResolvedValue({
      data: {
        data: {
          suggestion: {
            units: [],
            total_points: 0,
            archetype: 'Offensive Elite',
            playstyle: 'Shove It In',
            activation_count: 0,
            strategy_summary: 'Push the center.',
            warnings: [],
          },
          computed_total_points: 0,
          point_delta: 2000,
          reconciliation_warnings: [],
          army_list: null,
        },
        error: null,
      },
    })

    const result = await apiClient.suggestArmyList({
      faction: 1,
      point_limit: 2000,
      prompt: 'Aggressive elite list.',
      dry_run: true,
    })

    expect(result.point_delta).toBe(2000)
    expect(postRequest).toHaveBeenCalledWith('/advisor/suggest/', {
      faction: 1,
      point_limit: 2000,
      prompt: 'Aggressive elite list.',
      dry_run: true,
    })
  })
})
