import { useLayoutEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

const THEME_STORAGE_KEY = 'opr-helper-theme'

type ThemeMode = 'light' | 'dark'

type AppShellProps = {
  children: ReactNode
}

const navItems = [
  { label: 'Factions', to: '/' },
  { label: 'Lists', to: '/lists' },
  { label: 'Advisor', to: '/advisor' },
  { label: 'Calculator', to: '/calc' },
]

function systemPrefersDark(): boolean {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

function initialTheme(): ThemeMode {
  const saved = localStorage.getItem(THEME_STORAGE_KEY)
  if (saved === 'light' || saved === 'dark') {
    return saved
  }
  return systemPrefersDark() ? 'dark' : 'light'
}

function applyTheme(theme: ThemeMode) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  document.documentElement.dataset.theme = theme
}

export function AppShell({ children }: AppShellProps) {
  const location = useLocation()
  const [theme, setTheme] = useState<ThemeMode>(initialTheme)

  useLayoutEffect(() => {
    applyTheme(theme)
  }, [theme])

  function toggleTheme() {
    setTheme((currentTheme) => {
      const nextTheme = currentTheme === 'dark' ? 'light' : 'dark'
      localStorage.setItem(THEME_STORAGE_KEY, nextTheme)
      return nextTheme
    })
  }

  return (
    <main className="app-page">
      <header className="app-header">
        <div>
          <p className="app-kicker">OPR Helper</p>
          <p className="app-brand">Age of Fantasy tools</p>
        </div>
        <nav aria-label="Primary" className="app-nav">
          {navItems.map((item) => (
            <NavLink
              className={({ isActive }) => `app-nav-link ${isActive || isSectionActive(location.pathname, item.to) ? 'app-nav-link-active' : ''}`}
              end={item.to === '/'}
              key={item.to}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="app-button-secondary app-theme-toggle"
          onClick={toggleTheme}
          type="button"
        >
          {theme === 'dark' ? 'Light' : 'Dark'}
        </button>
      </header>
      <div className="app-content">{children}</div>
    </main>
  )
}

function isSectionActive(pathname: string, to: string): boolean {
  if (to === '/') {
    return pathname === '/' || pathname.startsWith('/factions/')
  }
  if (to === '/lists') {
    return pathname === '/lists' || pathname.startsWith('/lists/')
  }
  return pathname === to
}
