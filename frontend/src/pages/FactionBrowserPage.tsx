import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { Faction } from '../api/types'

export function FactionBrowserPage() {
  const [factions, setFactions] = useState<Faction[]>([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient
      .getFactions()
      .then(setFactions)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const normalizedQuery = query.trim().toLowerCase()
  const filteredFactions = normalizedQuery
    ? factions.filter((faction) => faction.name.toLowerCase().includes(normalizedQuery))
    : factions

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="app-kicker">Army books</p>
          <h1 className="app-heading mt-2">Age of Fantasy factions</h1>
          <p className="app-muted mt-2 text-sm">Browse army books, compare units, and start list-building from the faction roster.</p>
        </div>
        <Link className="app-button-primary" to="/lists">
          My lists
        </Link>
      </div>
      <label className="app-label mb-5 block max-w-xl">
        Search factions
        <input
          className="app-field mt-1 w-full"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter by faction name"
          type="search"
          value={query}
        />
      </label>
      {loading ? <p className="app-muted">Loading factions...</p> : null}
      {error ? <p className="app-alert-danger">{error}</p> : null}
      {!loading && !error && filteredFactions.length === 0 ? (
        <p className="app-card app-muted">No factions match your search.</p>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filteredFactions.map((faction) => (
          <Link
            className="app-card-link"
            key={faction.id}
            to={`/factions/${faction.id}`}
          >
            <h2 className="app-subheading">{faction.name}</h2>
            <p className="app-muted mt-2 text-sm">{faction.unit_count} units</p>
            <p className="mt-4 text-sm font-semibold" style={{ color: 'var(--color-accent)' }}>
              Browse faction
            </p>
          </Link>
        ))}
      </div>
    </section>
  )
}
