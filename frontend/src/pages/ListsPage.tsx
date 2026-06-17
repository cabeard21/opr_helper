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
            <Link className="text-sm font-semibold text-teal-700" to="/">
              Back to factions
            </Link>
            <h1 className="mt-2 text-3xl font-bold text-stone-950">Army lists</h1>
          </div>
        </div>
        {loading ? <p className="text-stone-600">Loading lists...</p> : null}
        {error ? <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p> : null}
        <div className="grid gap-3">
          {lists.map((list) => (
            <Link
              className="rounded-md border border-stone-200 bg-white p-4 shadow-sm hover:border-teal-500"
              key={list.id}
              to={`/lists/${list.id}`}
            >
              <h2 className="text-lg font-semibold text-stone-950">{list.name}</h2>
              <p className="mt-1 text-sm text-stone-600">
                {list.total_points.toLocaleString()} / {list.point_limit.toLocaleString()} pts
              </p>
            </Link>
          ))}
        </div>
      </div>
      <form className="rounded-md border border-stone-200 bg-white p-5 shadow-sm" onSubmit={handleCreate}>
        <h2 className="text-xl font-semibold text-stone-950">Create list</h2>
        <label className="mt-4 block text-sm font-medium text-stone-700">
          Name
          <input
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
        </label>
        <label className="mt-4 block text-sm font-medium text-stone-700">
          Faction
          <select
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
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
        <label className="mt-4 block text-sm font-medium text-stone-700">
          Point limit
          <input
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            min={1}
            onChange={(event) => setPointLimit(Number(event.target.value))}
            required
            type="number"
            value={pointLimit}
          />
        </label>
        <button className="mt-5 w-full rounded bg-stone-950 px-4 py-2 font-semibold text-white" type="submit">
          Create
        </button>
      </form>
    </section>
  )
}
