import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { ArmyList, Unit } from '../api/types'
import { ListBuilderPage } from './ListBuilderPage'

vi.mock('../api/client', () => ({
  apiClient: {
    getList: vi.fn(),
    getFactionUnits: vi.fn(),
    addListUnit: vi.fn(),
    updateListUnit: vi.fn(),
    removeListUnit: vi.fn(),
  },
}))

const paladins: Unit = {
  id: 10,
  faction: 1,
  name: 'Paladins',
  quality: 3,
  defense: 4,
  tough: 3,
  points: 180,
  special_rules: { Fearless: true },
  source_uid: 'unit-10',
  weapon_slots: [
    {
      id: 20,
      is_default: true,
      upgrade_cost: 0,
      weapon: {
        id: 30,
        name: 'Great Weapon',
        range: 0,
        attacks: 2,
        attacks_string: 'A2',
        ap: 2,
        special_rules: { Deadly: 3 },
        source_uid: 'weapon-30',
      },
    },
  ],
}

const emptyList: ArmyList = {
  id: 1,
  name: 'Tournament 2000',
  faction: 1,
  point_limit: 2000,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  total_points: 0,
  units: [],
}

const listWithPaladins: ArmyList = {
  ...emptyList,
  total_points: 180,
  units: [
    {
      id: 100,
      unit: paladins.id,
      unit_name: paladins.name,
      unit_points: paladins.points,
      model_count: 1,
      selected_weapon_slot: 20,
      selected_weapon_name: 'Great Weapon',
      notes: '',
      total_points: 180,
    },
  ],
}

describe('ListBuilderPage', () => {
  it('adds a unit, updates model count, and removes the row', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getList).mockResolvedValue(emptyList)
    vi.mocked(apiClient.getFactionUnits).mockResolvedValue([paladins])
    vi.mocked(apiClient.addListUnit).mockResolvedValue(listWithPaladins)
    vi.mocked(apiClient.updateListUnit).mockResolvedValue({
      ...listWithPaladins,
      total_points: 360,
      units: [{ ...listWithPaladins.units[0], model_count: 2, total_points: 360 }],
    })
    vi.mocked(apiClient.removeListUnit).mockResolvedValue(emptyList)

    render(
      <MemoryRouter initialEntries={['/lists/1']}>
        <Routes>
          <Route path="/lists/:id" element={<ListBuilderPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Tournament 2000' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /add paladins/i }))
    expect(await screen.findByText('180 / 2,000 pts')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /calculate paladins/i })).toHaveAttribute(
      'href',
      '/calc?factionId=1&unitId=10&weaponId=30',
    )

    await user.click(screen.getByRole('button', { name: /increase paladins/i }))

    await waitFor(() => {
      expect(apiClient.updateListUnit).toHaveBeenCalledWith(1, 100, { model_count: 2 })
    })
    expect(await screen.findByText('360 / 2,000 pts')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /remove paladins/i }))

    await waitFor(() => {
      expect(apiClient.removeListUnit).toHaveBeenCalledWith(1, 100)
    })
    expect(await screen.findByText('0 / 2,000 pts')).toBeInTheDocument()
  })
})
