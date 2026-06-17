import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { Unit } from '../api/types'
import { UnitCard } from '../components/UnitCard'

export function FactionUnitsPage() {
  const { id } = useParams()
  const factionId = Number(id)
  const invalidFactionId = !Number.isFinite(factionId) || factionId <= 0
  const [units, setUnits] = useState<Unit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!invalidFactionId)

  useEffect(() => {
    if (invalidFactionId) {
      return
    }

    apiClient
      .getFactionUnits(factionId)
      .then(setUnits)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [factionId, invalidFactionId])

  const pageError = invalidFactionId ? 'Faction not found.' : error

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link className="text-sm font-semibold text-teal-700" to="/">
            Back to factions
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-stone-950">Faction units</h1>
        </div>
        <Link className="rounded border border-stone-300 px-4 py-2 text-sm font-semibold" to="/lists">
          Open lists
        </Link>
      </div>
      {loading ? <p className="text-stone-600">Loading units...</p> : null}
      {pageError ? <p className="rounded border border-red-200 bg-red-50 p-3 text-red-700">{pageError}</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {units.map((unit) => (
          <UnitCard key={unit.id} unit={unit} />
        ))}
      </div>
    </section>
  )
}
