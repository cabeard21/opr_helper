import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { ArmyList, Faction } from '../api/types'

export function ListsPage() {
  const navigate = useNavigate()
  const [lists, setLists] = useState<ArmyList[]>([])
  const [factions, setFactions] = useState<Faction[]>([])
  const [name, setName] = useState('New AoF List')
  const [pointLimit, setPointLimit] = useState(2000)
  const [factionId, setFactionId] = useState<number | ''>('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([apiClient.getLists(), apiClient.getFactions()])
      .then(([nextLists, nextFactions]) => {
        setLists(nextLists)
        setFactions(nextFactions)
        setFactionId(nextFactions[0]?.id ?? '')
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!factionId) {
      setError('Choose a faction before creating a list.')
      return
    }

    try {
      const created = await apiClient.createList({
        name,
        faction: factionId,
        point_limit: pointLimit,
      })
      navigate(`/lists/${created.id}`)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div>
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <Link className="app-link" to="/">
              Back to factions
            </Link>
            <h1 className="app-heading mt-2">Army lists</h1>
          </div>
          <Link className="app-button-primary" to="/advisor">
            Army advisor
          </Link>
        </div>
        {loading ? <p className="app-muted">Loading lists...</p> : null}
        {error ? <p className="app-alert-danger mb-4">{error}</p> : null}
        <div className="grid gap-3">
          {!loading && lists.length === 0 ? (
            <p className="app-card app-muted">No lists yet. Create one here, or use the advisor to draft a starting point.</p>
          ) : null}
          {lists.map((list) => (
            <Link
              className="app-card-link p-4"
              key={list.id}
              to={`/lists/${list.id}`}
            >
              <h2 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>{list.name}</h2>
              <p className="app-muted mt-1 text-sm">
                {list.total_points.toLocaleString()} / {list.point_limit.toLocaleString()} pts
              </p>
            </Link>
          ))}
        </div>
      </div>
      <form className="app-card-lg" onSubmit={handleCreate}>
        <h2 className="app-subheading">Create list</h2>
        <label className="app-label mt-4 block">
          Name
          <input
            className="app-field mt-1 w-full"
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
        </label>
        <label className="app-label mt-4 block">
          Faction
          <select
            className="app-field mt-1 w-full"
            onChange={(event) => setFactionId(Number(event.target.value))}
            required
            value={factionId}
          >
            {factions.map((faction) => (
              <option key={faction.id} value={faction.id}>
                {faction.name}
              </option>
            ))}
          </select>
        </label>
        <label className="app-label mt-4 block">
          Point limit
          <input
            className="app-field mt-1 w-full"
            min={1}
            onChange={(event) => setPointLimit(Number(event.target.value))}
            required
            type="number"
            value={pointLimit}
          />
        </label>
        <button className="app-button-primary mt-5 w-full" type="submit">
          Create
        </button>
      </form>
    </section>
  )
}
