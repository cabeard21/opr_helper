import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { apiClient } from '../api/client'
import type { Faction } from '../api/types'
import { FactionBrowserPage } from './FactionBrowserPage'

vi.mock('../api/client', () => ({
  apiClient: {
    getFactions: vi.fn(),
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
  {
    id: 2,
    name: 'Beastmen',
    version: '3.5.3',
    last_fetched: null,
    source_uid: 'faction-beastmen',
    unit_count: 20,
  },
]

describe('FactionBrowserPage', () => {
  it('filters factions by search text and shows an empty result state', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.getFactions).mockResolvedValue(factions)

    render(
      <MemoryRouter>
        <FactionBrowserPage />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Kingdom of Angels' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Beastmen' })).toBeInTheDocument()

    await user.type(screen.getByRole('searchbox', { name: /search factions/i }), 'angel')

    expect(screen.getByRole('heading', { name: 'Kingdom of Angels' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Beastmen' })).not.toBeInTheDocument()

    await user.clear(screen.getByRole('searchbox', { name: /search factions/i }))
    await user.type(screen.getByRole('searchbox', { name: /search factions/i }), 'rat')

    expect(screen.getByText('No factions match your search.')).toBeInTheDocument()
  })
})
