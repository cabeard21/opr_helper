import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { AdvisorSuggestionResponse, ArmyList, Faction } from '../api/types'
import { AdvisorPage } from './AdvisorPage'

vi.mock('../api/client', () => ({
  apiClient: {
    getFactions: vi.fn(),
    suggestArmyList: vi.fn(),
  },
}))

const factions: Faction[] = [
  {
    id: 1,
    name: 'Kingdom of Angels',
    version: '3.5.3',
    last_fetched: null,
    source_uid: 'faction-angels',
    unit_count: 12,
  },
]

const createdList: ArmyList = {
  id: 44,
  name: 'Kingdom of Angels - Offensive Elite (2000 pts)',
  faction: 1,
  point_limit: 2000,
  advisor_archetype: 'Offensive Elite',
  advisor_playstyle: 'Shove It In',
  advisor_strategy_summary: 'Push Paladins through the center.',
  advisor_prompt: 'Aggressive elite list with anti-tough damage.',
  advisor_warnings: ['Low activation count.'],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  total_points: 180,
  validation: { errors: [], warnings: [] },
  units: [],
}

const previewResponse: AdvisorSuggestionResponse = {
  suggestion: {
    units: [
      {
        unit_id: 10,
        unit_name: 'Paladins',
        model_count: 5,
        combined_from_count: 2,
        selected_upgrade_ids: [],
        parent_unit_index: null,
        justification: 'Durable high-AP center pressure.',
      },
      {
        unit_id: 11,
        unit_name: 'Champion',
        model_count: 1,
        combined_from_count: 1,
        selected_upgrade_ids: [],
        parent_unit_index: 0,
        justification: 'Embedded aura support.',
      },
    ],
    total_points: 180,
    archetype: 'Offensive Elite',
    playstyle: 'Shove It In',
    activation_count: 1,
    strategy_summary: 'Push Paladins through the center while cheaper units score.',
    warnings: ['Low activation count.'],
  },
  computed_total_points: 180,
  point_delta: 1820,
  reconciliation_warnings: ['Paladins model count was reduced to the maximum of 1.'],
  army_list: null,
}

describe('AdvisorPage', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('previews an advisor suggestion and creates the generated list', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getFactions).mockResolvedValue(factions)
    vi.mocked(apiClient.suggestArmyList)
      .mockResolvedValueOnce(previewResponse)
      .mockResolvedValueOnce({ ...previewResponse, army_list: createdList })

    render(
      <MemoryRouter initialEntries={['/advisor']}>
        <Routes>
          <Route path="/advisor" element={<AdvisorPage />} />
          <Route path="/lists/:id" element={<h1>Created list</h1>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Army advisor' })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText(/faction/i), '1')
    await user.clear(screen.getByLabelText(/point limit/i))
    await user.type(screen.getByLabelText(/point limit/i), '2000')
    await user.type(screen.getByLabelText(/goal/i), 'Aggressive elite list with anti-tough damage.')
    await user.click(screen.getByRole('button', { name: /preview suggestion/i }))

    expect(await screen.findByText('Offensive Elite')).toBeInTheDocument()
    expect(screen.getByText('Shove It In')).toBeInTheDocument()
    expect(screen.getByText('180 / 2,000 pts')).toBeInTheDocument()
    expect(screen.getByText('Paladins')).toBeInTheDocument()
    expect(screen.getByText('x5, combined x2')).toBeInTheDocument()
    expect(screen.getByText(/Durable high-AP/)).toBeInTheDocument()
    expect(screen.getByText('Champion')).toBeInTheDocument()
    expect(screen.getByText(/Embedded in Paladins/)).toBeInTheDocument()
    expect(screen.getByText(/Low activation count/)).toBeInTheDocument()
    expect(screen.getByText(/model count was reduced/)).toBeInTheDocument()
    expect(apiClient.suggestArmyList).toHaveBeenCalledWith({
      faction: 1,
      point_limit: 2000,
      prompt: 'Aggressive elite list with anti-tough damage.',
      dry_run: true,
    })

    await user.click(screen.getByRole('button', { name: /create list/i }))

    await waitFor(() => {
      expect(apiClient.suggestArmyList).toHaveBeenLastCalledWith({
        faction: 1,
        point_limit: 2000,
        prompt: 'Aggressive elite list with anti-tough damage.',
        dry_run: false,
        suggestion: previewResponse.suggestion,
      })
    })
    expect(await screen.findByRole('heading', { name: 'Created list' })).toBeInTheDocument()
  })

  it('requires a goal before requesting a suggestion', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getFactions).mockResolvedValue(factions)

    render(
      <MemoryRouter initialEntries={['/advisor']}>
        <Routes>
          <Route path="/advisor" element={<AdvisorPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Army advisor' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /preview suggestion/i }))

    expect(await screen.findByText('Describe what you want the list to do.')).toBeInTheDocument()
    expect(apiClient.suggestArmyList).not.toHaveBeenCalled()
  })
})
