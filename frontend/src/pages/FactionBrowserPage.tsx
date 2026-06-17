import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { Faction } from '../api/types'

export function FactionBrowserPage() {
  const [factions, setFactions] = useState<Faction[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient
      .getFactions()
      .then(setFactions)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase text-teal-700">OPR Helper</p>
          <h1 className="mt-2 text-3xl font-bold text-stone-950">Age of Fantasy factions</h1>
        </div>
        <Link className="rounded bg-stone-950 px-4 py-2 text-sm font-semibold text-white" to="/lists">
          My lists
        </Link>
      </div>
      {loading ? <p className="text-stone-600">Loading factions...</p> : null}
      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p> : null}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {factions.map((faction) => (
          <Link
            className="rounded-md border border-stone-200 bg-white p-5 shadow-sm hover:border-teal-500"
            key={faction.id}
            to={`/factions/${faction.id}`}
          >
            <h2 className="text-xl font-semibold text-stone-950">{faction.name}</h2>
            <p className="mt-2 text-sm text-stone-600">{faction.unit_count} units</p>
            <p className="mt-4 text-sm font-semibold text-teal-700">Browse faction</p>
          </Link>
        ))}
      </div>
    </section>
  )
}
