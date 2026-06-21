import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { ArmyList, Unit } from '../api/types'
import { ListBuilderPage } from './ListBuilderPage'

vi.mock('../api/client', () => ({
  apiClient: {
    getList: vi.fn(),
    getFactionUnits: vi.fn(),
    analyzeList: vi.fn(),
    exportArmyForgeList: vi.fn(),
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
  max_models: 2,
  default_models: 1,
  special_rules: { Fearless: true },
  source_uid: 'unit-10',
  weapon_slots: [
    {
      id: 20,
      is_default: true,
      upgrade_cost: 0,
      option_id: null,
      upgrade_id: null,
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
      option_id: 'option-blessed-weapons',
      upgrade_id: 'upgrade-blessed-great',
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
  upgrade_sections: [],
}

const archers: Unit = {
  ...paladins,
  id: 11,
  name: 'Archers',
  points: 90,
  source_uid: 'unit-11',
  weapon_slots: [
    {
      ...paladins.weapon_slots[0],
      id: 22,
      weapon: {
        ...paladins.weapon_slots[0].weapon,
        id: 32,
        name: 'Longbow',
        source_uid: 'weapon-32',
      },
    },
  ],
}

const bullConstruct: Unit = {
  ...paladins,
  id: 12,
  name: 'Bull Construct',
  quality: 4,
  defense: 2,
  tough: 9,
  points: 235,
  source_uid: 'bOv6BGK',
  weapon_slots: [
    {
      ...paladins.weapon_slots[0],
      id: 23,
      weapon: {
        ...paladins.weapon_slots[0].weapon,
        id: 33,
        name: 'Heavy Great Weapon',
        attacks: 6,
        attacks_string: 'A6',
        ap: 4,
        source_uid: 'BTEKkW8x',
      },
    },
    {
      ...paladins.weapon_slots[0],
      id: 24,
      weapon: {
        ...paladins.weapon_slots[0].weapon,
        id: 34,
        name: 'Stomp',
        attacks: 3,
        attacks_string: 'A3',
        ap: 1,
        source_uid: 'qSPHZX1J',
      },
    },
  ],
  upgrade_sections: [
    {
      id: 40,
      package_uid: 'X2LU7GIa',
      section_uid: 'm5Fl4_I9XF',
      label: 'Replace Heavy Great Weapon',
      variant: 'replace',
      targets: ['Heavy Great Weapon'],
      options: [
        {
          id: 41,
          option_uid: '2-liYIN7tu',
          label: 'Twin Arm-Flamethrowers',
          cost: 35,
          gains: [],
          weapons: [
            {
              id: 35,
              name: 'Twin Arm-Flamethrowers',
              range: 12,
              attacks: 3,
              attacks_string: 'A3',
              ap: 1,
              special_rules: { Blast: 3, Reliable: true },
              source_uid: '3fOjuT5u',
            },
          ],
        },
      ],
    },
  ],
}

const emptyList: ArmyList = {
  id: 1,
  name: 'Tournament 2000',
  faction: 1,
  point_limit: 2000,
  advisor_archetype: 'Offensive Elite',
  advisor_playstyle: 'Shove It In',
  advisor_strategy_summary: 'Push through the center.',
  advisor_prompt: 'Aggressive elite list.',
  advisor_warnings: ['Low activation count.'],
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
      selected_upgrades: [],
      loadout_weapon_names: ['Great Weapon'],
      loadout_summary: 'Great Weapon',
      parent_entry: null,
      combined_from_count: 1,
      notes: '',
      total_points: 180,
    },
  ],
}

const listWithBull: ArmyList = {
  ...emptyList,
  total_points: 235,
  units: [
    {
      id: 101,
      unit: bullConstruct.id,
      unit_name: bullConstruct.name,
      unit_points: bullConstruct.points,
      model_count: 1,
      selected_weapon_slot: null,
      selected_weapon_name: null,
      selected_upgrades: [],
      loadout_weapon_names: ['Heavy Great Weapon', 'Stomp'],
      loadout_summary: 'Heavy Great Weapon + Stomp',
      parent_entry: null,
      combined_from_count: 1,
      notes: '',
      total_points: 235,
    },
  ],
}

const secondList: ArmyList = {
  ...emptyList,
  id: 2,
  name: 'Second Draft',
  units: [],
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve
  })
  return { promise, resolve }
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

  it('clears stale army list content while navigating between list routes', async () => {
    const user = userEvent.setup()
    const nextList = deferred<ArmyList>()
    vi.mocked(apiClient.getList).mockImplementation((listId) =>
      listId === 1 ? Promise.resolve(listWithPaladins) : nextList.promise,
    )
    vi.mocked(apiClient.getFactionUnits).mockResolvedValue([paladins])

    render(
      <MemoryRouter initialEntries={['/lists/1']}>
        <Link to="/lists/2">Open second list</Link>
        <Routes>
          <Route path="/lists/:id" element={<ListBuilderPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Tournament 2000' })).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: /open second list/i }))

    expect(screen.getByText('Loading army list...')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Tournament 2000' })).not.toBeInTheDocument()

    nextList.resolve(secondList)

    expect(await screen.findByRole('heading', { name: 'Second Draft' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Tournament 2000' })).not.toBeInTheDocument()
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

  it('updates native upgrade sections from the list row', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getList).mockResolvedValue(listWithBull)
    vi.mocked(apiClient.getFactionUnits).mockResolvedValue([bullConstruct])
    vi.mocked(apiClient.updateListUnit).mockResolvedValue({
      ...listWithBull,
      total_points: 270,
      units: [
        {
          ...listWithBull.units[0],
          selected_upgrades: [41],
          loadout_weapon_names: ['Stomp', 'Twin Arm-Flamethrowers'],
          loadout_summary: 'Stomp + Twin Arm-Flamethrowers',
          total_points: 270,
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
    expect(screen.getByRole('option', { name: /Twin Arm-Flamethrowers \(\+35 pts\)/i })).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText(/replace heavy great weapon for bull construct/i), '41')

    await waitFor(() => {
      expect(apiClient.updateListUnit).toHaveBeenCalledWith(1, 101, { selected_upgrades: [41] })
    })
    expect(await screen.findByText('270 / 2,000 pts')).toBeInTheDocument()
  })

  it('loads list analysis and exports Army Forge JSON without a share link', async () => {
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
          effective_wounds: 18,
          effective_wounds_per_100_points: 10,
          weapon_id: 30,
          weapon_name: 'Great Weapon',
          target_results: [
            {
              target_id: 'infantry',
              ev: 1.25,
              ranged_ev: 0,
              melee_ev: 1.25,
              wounds_per_100_points: 0.69,
              ranged_wounds_per_100_points: 0,
              melee_wounds_per_100_points: 0.69,
              p_kill_model: 0.8,
            },
            {
              target_id: 'elite',
              ev: 0.75,
              ranged_ev: 0,
              melee_ev: 0.75,
              wounds_per_100_points: 0.42,
              ranged_wounds_per_100_points: 0,
              melee_wounds_per_100_points: 0.42,
              p_kill_model: 0.3,
            },
            {
              target_id: 'monster',
              ev: 0.5,
              ranged_ev: 0,
              melee_ev: 0.5,
              wounds_per_100_points: 0.28,
              ranged_wounds_per_100_points: 0,
              melee_wounds_per_100_points: 0.28,
              p_kill_model: 0.1,
            },
          ],
        },
      ],
      totals: [
        {
          target_id: 'infantry',
          ev: 1.25,
          ranged_ev: 0,
          melee_ev: 1.25,
          wounds_per_100_points: 0.69,
          ranged_wounds_per_100_points: 0,
          melee_wounds_per_100_points: 0.69,
        },
        {
          target_id: 'elite',
          ev: 0.75,
          ranged_ev: 0,
          melee_ev: 0.75,
          wounds_per_100_points: 0.42,
          ranged_wounds_per_100_points: 0,
          melee_wounds_per_100_points: 0.42,
        },
        {
          target_id: 'monster',
          ev: 0.5,
          ranged_ev: 0,
          melee_ev: 0.5,
          wounds_per_100_points: 0.28,
          ranged_wounds_per_100_points: 0,
          melee_wounds_per_100_points: 0.28,
        },
      ],
    })
    vi.mocked(apiClient.exportArmyForgeList).mockResolvedValue({
      id: 'opr-1',
      list: {
        id: 'opr-1',
        key: 'opr-key-1',
        name: 'Tournament 2000',
        units: [
          {
            id: 'unit-10',
            xp: 0,
            notes: null,
            armyId: 'faction-angels',
            traits: [],
            combined: false,
            joinToUnit: null,
            selectionId: 'sel-100-0',
            selectedUpgrades: [],
          },
        ],
        isCloud: false,
        forceOrg: true,
        modified: '2026-01-01T00:00:00.000Z',
        gameSystem: 'aof',
        modelCount: 1,
        simpleMode: false,
        description: '',
        pointsLimit: 2000,
        campaignMode: false,
        cloudModified: '2026-01-01T00:00:00.000Z',
        narrativeMode: false,
        activationCount: 1,
      },
      armyId: 'faction-angels',
      armyIds: ['faction-angels'],
      armyName: 'Kingdom of Angels',
      modified: '2026-01-01T00:00:00.000Z',
      favourite: false,
      gameSystem: 'aof',
      listPoints: 180,
      armyFaction: null,
      saveVersion: 3,
      armyVersions: [{ armyId: 'faction-angels', version: '3.5.3' }],
    })

    render(
      <MemoryRouter initialEntries={['/lists/1']}>
        <Routes>
          <Route path="/lists/:id" element={<ListBuilderPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Tournament 2000' })).toBeInTheDocument()
    expect(screen.getByText('Offensive Elite')).toBeInTheDocument()
    expect(screen.getByText('Shove It In')).toBeInTheDocument()
    expect(screen.getByText('Push through the center.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /create share link/i })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /analysis/i }))

    expect(await screen.findByRole('heading', { name: /army analysis/i })).toBeInTheDocument()
    expect(apiClient.analyzeList).toHaveBeenCalledWith(1, expect.arrayContaining([
      expect.objectContaining({ id: 'infantry' }),
    ]))
    expect(screen.getAllByText('1.25 total EV').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Ranged 0.00 / Melee 1.25').length).toBeGreaterThan(0)
    expect(screen.getAllByText('18.00 toughness').length).toBeGreaterThan(0)
    expect(screen.getAllByText('0.69 wounds / 100 pts').length).toBeGreaterThan(0)
    const graph = screen.getByRole('img', { name: /balanced list web graph/i })
    expect(graph).toBeInTheDocument()
    expect(within(graph).getByText('Activation')).toBeInTheDocument()
    expect(within(graph).getByText('Reach')).toBeInTheDocument()
    expect(within(graph).getByText('Damage')).toBeInTheDocument()
    expect(within(graph).getByText('Durability')).toBeInTheDocument()
    expect(within(graph).getByText('Coverage')).toBeInTheDocument()
    expect(within(graph).getByText('Balance')).toBeInTheDocument()
    expect(screen.getByText('Balanced list profile')).toBeInTheDocument()
    expect(screen.getByText('Activation Health')).toBeInTheDocument()
    expect(screen.getByText('Objective Reach')).toBeInTheDocument()
    expect(screen.getByText('Damage Pressure')).toBeInTheDocument()
    expect(screen.getAllByText('Durability').length).toBeGreaterThan(0)
    expect(screen.getByText('Threat Coverage')).toBeInTheDocument()
    expect(screen.getByText('Battleline Balance')).toBeInTheDocument()
    expect(screen.getByText(/1 effective activations \/ target 7/i)).toBeInTheDocument()
    expect(screen.getByText(/0% ranged \/ 100% melee/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^toughness$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /toughness \/ 100 pts/i })).toBeInTheDocument()
    expect(screen.getByText('10.00')).toBeInTheDocument()
    expect(screen.getByText(/best vs infantry/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /export army forge/i }))

    await waitFor(() => {
      expect(apiClient.exportArmyForgeList).toHaveBeenCalledWith(1)
    })
  })

  it('sorts analysis table by unit name and target efficiency', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getList).mockResolvedValue(listWithPaladins)
    vi.mocked(apiClient.getFactionUnits).mockResolvedValue([paladins, archers])
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
          effective_wounds: 18,
          effective_wounds_per_100_points: 10,
          weapon_id: 30,
          weapon_name: 'Great Weapon',
          target_results: [
            {
              target_id: 'infantry',
              ev: 1.25,
              ranged_ev: 0,
              melee_ev: 1.25,
              wounds_per_100_points: 0.69,
              ranged_wounds_per_100_points: 0,
              melee_wounds_per_100_points: 0.69,
              p_kill_model: 0.8,
            },
            {
              target_id: 'elite',
              ev: 0.75,
              ranged_ev: 0,
              melee_ev: 0.75,
              wounds_per_100_points: 0.42,
              ranged_wounds_per_100_points: 0,
              melee_wounds_per_100_points: 0.42,
              p_kill_model: 0.3,
            },
            {
              target_id: 'monster',
              ev: 0.5,
              ranged_ev: 0,
              melee_ev: 0.5,
              wounds_per_100_points: 0.28,
              ranged_wounds_per_100_points: 0,
              melee_wounds_per_100_points: 0.28,
              p_kill_model: 0.1,
            },
          ],
        },
        {
          list_unit_id: 101,
          unit_id: 11,
          unit_name: 'Archers',
          model_count: 1,
          points: 90,
          effective_wounds: 12,
          effective_wounds_per_100_points: 13.33,
          weapon_id: 32,
          weapon_name: 'Longbow',
          target_results: [
            {
              target_id: 'infantry',
              ev: 0.5,
              ranged_ev: 0.5,
              melee_ev: 0,
              wounds_per_100_points: 0.56,
              ranged_wounds_per_100_points: 0.56,
              melee_wounds_per_100_points: 0,
              p_kill_model: 0.4,
            },
            {
              target_id: 'elite',
              ev: 0.5,
              ranged_ev: 0.5,
              melee_ev: 0,
              wounds_per_100_points: 0.8,
              ranged_wounds_per_100_points: 0.8,
              melee_wounds_per_100_points: 0,
              p_kill_model: 0.2,
            },
            {
              target_id: 'monster',
              ev: 0.1,
              ranged_ev: 0.1,
              melee_ev: 0,
              wounds_per_100_points: 0.11,
              ranged_wounds_per_100_points: 0.11,
              melee_wounds_per_100_points: 0,
              p_kill_model: 0.01,
            },
          ],
        },
      ],
      totals: [
        {
          target_id: 'infantry',
          ev: 1.75,
          ranged_ev: 0.5,
          melee_ev: 1.25,
          wounds_per_100_points: 0.65,
          ranged_wounds_per_100_points: 0.19,
          melee_wounds_per_100_points: 0.46,
        },
        {
          target_id: 'elite',
          ev: 1.25,
          ranged_ev: 0.5,
          melee_ev: 0.75,
          wounds_per_100_points: 0.46,
          ranged_wounds_per_100_points: 0.19,
          melee_wounds_per_100_points: 0.28,
        },
        {
          target_id: 'monster',
          ev: 0.6,
          ranged_ev: 0.1,
          melee_ev: 0.5,
          wounds_per_100_points: 0.22,
          ranged_wounds_per_100_points: 0.04,
          melee_wounds_per_100_points: 0.19,
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
    await user.click(screen.getByRole('button', { name: /analysis/i }))
    expect(await screen.findByRole('heading', { name: /army analysis/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /unit/i }))
    expect(tableUnitNames()).toEqual(['Archers', 'Paladins'])

    await user.click(screen.getByRole('button', { name: /elite wounds \/ 100 pts/i }))
    expect(tableUnitNames()).toEqual(['Archers', 'Paladins'])

    await user.click(screen.getByRole('button', { name: /^toughness$/i }))
    expect(tableUnitNames()).toEqual(['Paladins', 'Archers'])
  })
})

function tableUnitNames() {
  return screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => row.querySelector('td')?.textContent ?? '')
}
