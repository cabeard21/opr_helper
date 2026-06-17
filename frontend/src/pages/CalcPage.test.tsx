import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { CalcResult, Faction, Unit } from '../api/types'
import { CalcPage } from './CalcPage'

vi.mock('../api/client', () => ({
  apiClient: {
    getFactions: vi.fn(),
    getFactionUnits: vi.fn(),
    calculateEv: vi.fn(),
  },
}))

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div role="img">{children}</div>,
  Bar: () => <div />,
  CartesianGrid: () => <div />,
  ReferenceLine: () => <div />,
  Tooltip: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
}))

const factions: Faction[] = [
  {
    id: 1,
    name: 'Kingdom of Angels',
    version: '3.5.3',
    last_fetched: null,
    source_uid: 'faction-angels',
    unit_count: 1,
  },
]

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

const calcResult: CalcResult = {
  ev: 3.333333,
  distribution: [
    { wounds: 0, probability: 0.2 },
    { wounds: 3, probability: 0.8 },
  ],
  p_zero_wounds: 0.2,
  p_kill_model: 0.8,
  p_kill_unit: 0.8,
}

function renderCalcPage(path = '/calc') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/calc" element={<CalcPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CalcPage', () => {
  it('calculates expected wounds for a selected attacker and target', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getFactions).mockResolvedValue(factions)
    vi.mocked(apiClient.getFactionUnits).mockResolvedValue([paladins])
    vi.mocked(apiClient.calculateEv).mockResolvedValue(calcResult)

    renderCalcPage()

    await user.selectOptions(await screen.findByLabelText(/faction/i), '1')
    await user.selectOptions(await screen.findByLabelText(/unit/i), '10')
    await user.selectOptions(await screen.findByLabelText(/weapon/i), '30')
    await user.click(screen.getByRole('button', { name: /calculate/i }))

    await waitFor(() => {
      expect(apiClient.calculateEv).toHaveBeenCalledWith({
        unit_id: 10,
        weapon_id: 30,
        target: { defense: 5, tough: 1 },
        modifiers: { stealth: false, indirect: false },
      })
    })
    expect(await screen.findByText('3.33')).toBeInTheDocument()
    expect(screen.getAllByText('80.0%')).toHaveLength(2)
    expect(screen.getByRole('img', { name: /wound probability histogram/i })).toBeInTheDocument()
  })

  it('prefills selections from valid query parameters', async () => {
    vi.mocked(apiClient.getFactions).mockResolvedValue(factions)
    vi.mocked(apiClient.getFactionUnits).mockResolvedValue([paladins])
    vi.mocked(apiClient.calculateEv).mockResolvedValue(calcResult)

    renderCalcPage('/calc?factionId=1&unitId=10&weaponId=30')

    const attackerPanel = await screen.findByRole('region', { name: /attacker/i })

    await waitFor(() => {
      expect(within(attackerPanel).getByLabelText(/faction/i)).toHaveValue('1')
      expect(within(attackerPanel).getByLabelText(/unit/i)).toHaveValue('10')
      expect(within(attackerPanel).getByLabelText(/weapon/i)).toHaveValue('30')
    })
  })
})
