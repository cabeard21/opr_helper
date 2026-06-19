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
          <Link className="app-link" to="/">
            Back to factions
          </Link>
          <h1 className="app-heading mt-2">Faction units</h1>
        </div>
        <Link className="app-button-secondary" to="/lists">
          Open lists
        </Link>
      </div>
      {loading ? <p className="app-muted">Loading units...</p> : null}
      {pageError ? <p className="app-alert-danger">{pageError}</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {units.map((unit) => (
          <UnitCard key={unit.id} unit={unit} />
        ))}
      </div>
    </section>
  )
}
