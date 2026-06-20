import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { ArmyList, Faction } from '../api/types'
import { ListsPage } from './ListsPage'

vi.mock('../api/client', () => ({
  apiClient: {
    getLists: vi.fn(),
    getFactions: vi.fn(),
    createList: vi.fn(),
    deleteList: vi.fn(),
  },
}))

const faction: Faction = {
  id: 1,
  name: 'Kingdom of Angels',
  version: '3.5.3',
  last_fetched: null,
  source_uid: 'faction-angels',
  unit_count: 12,
}

const armyList: ArmyList = {
  id: 44,
  name: 'Tournament 2000',
  faction: 1,
  point_limit: 2000,
  advisor_archetype: '',
  advisor_playstyle: '',
  advisor_strategy_summary: '',
  advisor_prompt: '',
  advisor_warnings: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  total_points: 180,
  validation: { errors: [], warnings: [] },
  units: [],
}

describe('ListsPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('deletes an army list after confirmation', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getLists).mockResolvedValue([armyList])
    vi.mocked(apiClient.getFactions).mockResolvedValue([faction])
    vi.mocked(apiClient.deleteList).mockResolvedValue({ deleted: true })
    vi.stubGlobal('confirm', vi.fn(() => true))

    render(
      <MemoryRouter initialEntries={['/lists']}>
        <Routes>
          <Route path="/lists" element={<ListsPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('link', { name: /tournament 2000/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /delete tournament 2000/i }))

    await waitFor(() => {
      expect(apiClient.deleteList).toHaveBeenCalledWith(44)
    })
    expect(screen.queryByRole('link', { name: /tournament 2000/i })).not.toBeInTheDocument()
  })
})
