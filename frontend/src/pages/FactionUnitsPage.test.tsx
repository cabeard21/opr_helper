import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { Unit } from '../api/types'
import { FactionUnitsPage } from './FactionUnitsPage'

vi.mock('../api/client', () => ({
  apiClient: {
    getFactionUnits: vi.fn(),
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
  special_rules: {},
  source_uid: 'unit-paladins',
  weapon_slots: [],
  upgrade_sections: [],
}

const archers: Unit = {
  ...paladins,
  id: 11,
  faction: 2,
  name: 'Archers',
  source_uid: 'unit-archers',
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve
  })
  return { promise, resolve }
}

describe('FactionUnitsPage', () => {
  it('clears stale faction units while navigating between faction routes', async () => {
    const user = userEvent.setup()
    const nextUnits = deferred<Unit[]>()
    vi.mocked(apiClient.getFactionUnits).mockImplementation((factionId) =>
      factionId === 1 ? Promise.resolve([paladins]) : nextUnits.promise,
    )

    render(
      <MemoryRouter initialEntries={['/factions/1']}>
        <Link to="/factions/2">Open second faction</Link>
        <Routes>
          <Route path="/factions/:id" element={<FactionUnitsPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Paladins')).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: /open second faction/i }))

    expect(screen.getByText('Loading units...')).toBeInTheDocument()
    expect(screen.queryByText('Paladins')).not.toBeInTheDocument()

    nextUnits.resolve([archers])

    expect(await screen.findByText('Archers')).toBeInTheDocument()
    expect(screen.queryByText('Paladins')).not.toBeInTheDocument()
  })
})
