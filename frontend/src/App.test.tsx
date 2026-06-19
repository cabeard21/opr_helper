import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from './api/client'
import type { Faction } from './api/types'
import App from './App'

vi.mock('./api/client', () => ({
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
]

function renderApp(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('App shell', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
    vi.mocked(apiClient.getFactions).mockResolvedValue(factions)
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('dark'),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    })
  })

  it('shows global navigation to the main app tools', async () => {
    renderApp('/advisor')

    const navigation = screen.getByRole('navigation', { name: /primary/i })
    expect(within(navigation).getByRole('link', { name: /factions/i })).toHaveAttribute('href', '/')
    expect(within(navigation).getByRole('link', { name: /lists/i })).toHaveAttribute('href', '/lists')
    expect(within(navigation).getByRole('link', { name: /advisor/i })).toHaveAttribute('href', '/advisor')
    expect(within(navigation).getByRole('link', { name: /calculator/i })).toHaveAttribute('href', '/calc')
    expect(within(navigation).getByRole('link', { name: /advisor/i })).toHaveAttribute('aria-current', 'page')
  })

  it('uses system dark mode, then persists a manual theme override', async () => {
    const user = userEvent.setup()

    renderApp('/')

    expect(document.documentElement).toHaveClass('dark')
    await user.click(screen.getByRole('button', { name: /switch to light mode/i }))

    expect(document.documentElement).not.toHaveClass('dark')
    expect(localStorage.getItem('opr-helper-theme')).toBe('light')
    expect(screen.getByRole('button', { name: /switch to dark mode/i })).toBeInTheDocument()
  })
})
