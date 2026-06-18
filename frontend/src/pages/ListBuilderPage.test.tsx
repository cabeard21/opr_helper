import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { ArmyList, Unit } from '../api/types'
import { ListBuilderPage } from './ListBuilderPage'

vi.mock('../api/client', () => ({
  apiClient: {
    getList: vi.fn(),
    getFactionUnits: vi.fn(),
    analyzeList: vi.fn(),
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
  min_models: 1,
  max_models: null,
  default_models: 1,
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
    {
      id: 21,
      is_default: false,
      upgrade_cost: 25,
      weapon: {
        id: 31,
        name: 'Blessed Great Weapon',
        range: 0,
        attacks: 2,
        attacks_string: 'A2',
        ap: 3,
        special_rules: { Deadly: 3 },
        source_uid: 'weapon-31',
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
  validation: { errors: [], warnings: [] },
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
  beforeEach(() => {
    vi.stubGlobal('location', {
      origin: 'http://localhost:5173',
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

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

  it('updates selected weapon upgrades from the list row', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getList).mockResolvedValue(listWithPaladins)
    vi.mocked(apiClient.getFactionUnits).mockResolvedValue([paladins])
    vi.mocked(apiClient.updateListUnit).mockResolvedValue({
      ...listWithPaladins,
      total_points: 205,
      units: [
        {
          ...listWithPaladins.units[0],
          selected_weapon_slot: 21,
          selected_weapon_name: 'Blessed Great Weapon',
          total_points: 205,
        },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/lists/1']}>
        <Routes>
          <Route path="/lists/:id" element={<ListBuilderPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Tournament 2000' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Blessed Great Weapon \(\+25 pts\)/i })).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText(/weapon for paladins/i), '21')

    await waitFor(() => {
      expect(apiClient.updateListUnit).toHaveBeenCalledWith(1, 100, { selected_weapon_slot: 21 })
    })
    expect(await screen.findByText('205 / 2,000 pts')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /calculate paladins/i })).toHaveAttribute(
      'href',
      '/calc?factionId=1&unitId=10&weaponId=31',
    )
  })

  it('loads list analysis and creates a read-only share URL', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getList).mockResolvedValue(listWithPaladins)
    vi.mocked(apiClient.getFactionUnits).mockResolvedValue([paladins])
    vi.mocked(apiClient.analyzeList).mockResolvedValue({
      list_id: 1,
      targets: [
        { id: 'infantry', name: 'Infantry', defense: 5, tough: 1 },
        { id: 'elite', name: 'Elite', defense: 3, tough: 3 },
        { id: 'monster', name: 'Monster', defense: 2, tough: 10 },
      ],
      units: [
        {
          list_unit_id: 100,
          unit_id: 10,
          unit_name: 'Paladins',
          model_count: 1,
          points: 180,
          weapon_id: 30,
          weapon_name: 'Great Weapon',
          target_results: [
            { target_id: 'infantry', ev: 1.25, wounds_per_100_points: 0.69, p_kill_model: 0.8 },
            { target_id: 'elite', ev: 0.75, wounds_per_100_points: 0.42, p_kill_model: 0.3 },
            { target_id: 'monster', ev: 0.5, wounds_per_100_points: 0.28, p_kill_model: 0.1 },
          ],
        },
      ],
      totals: [
        { target_id: 'infantry', ev: 1.25, wounds_per_100_points: 0.69 },
        { target_id: 'elite', ev: 0.75, wounds_per_100_points: 0.42 },
        { target_id: 'monster', ev: 0.5, wounds_per_100_points: 0.28 },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/lists/1']}>
        <Routes>
          <Route path="/lists/:id" element={<ListBuilderPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Tournament 2000' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /analysis/i }))

    expect(await screen.findByRole('heading', { name: /army analysis/i })).toBeInTheDocument()
    expect(apiClient.analyzeList).toHaveBeenCalledWith(1, expect.arrayContaining([
      expect.objectContaining({ id: 'infantry' }),
    ]))
    expect(screen.getByText('1.25')).toBeInTheDocument()
    expect(screen.getByText('0.69')).toBeInTheDocument()
    expect(screen.getByText(/best vs infantry/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /create share link/i }))

    const shareLink = await screen.findByLabelText(/share url/i)
    expect((shareLink as HTMLInputElement).value).toContain('/lists/shared?share=')
  })
})
