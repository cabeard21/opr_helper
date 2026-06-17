import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { ArmyList, ListUnit, Unit } from '../api/types'
import { PointTracker } from '../components/PointTracker'
import { UnitCard } from '../components/UnitCard'

export function ListBuilderPage() {
  const { id } = useParams()
  const listId = Number(id)
  const invalidListId = !Number.isFinite(listId) || listId <= 0
  const [armyList, setArmyList] = useState<ArmyList | null>(null)
  const [units, setUnits] = useState<Unit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!invalidListId)
  const [busyUnitId, setBusyUnitId] = useState<number | null>(null)

  useEffect(() => {
    if (invalidListId) {
      return
    }

    apiClient
      .getList(listId)
      .then(async (list) => {
        setArmyList(list)
        setUnits(await apiClient.getFactionUnits(list.faction))
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [listId, invalidListId])

  const unitLookup = useMemo(() => new Map(units.map((unit) => [unit.id, unit])), [units])

  async function addUnit(unit: Unit) {
    if (!armyList) {
      return
    }
    const defaultSlot = unit.weapon_slots.find((slot) => slot.is_default) ?? unit.weapon_slots[0]
    setBusyUnitId(unit.id)
    setError(null)
    try {
      setArmyList(
        await apiClient.addListUnit(armyList.id, {
          unit: unit.id,
          model_count: 1,
          selected_weapon_slot: defaultSlot?.id ?? null,
          notes: '',
        }),
      )
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function updateModelCount(entry: ListUnit, nextCount: number) {
    if (!armyList || nextCount < 1) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(armyList.id, entry.id, { model_count: nextCount }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function removeUnit(entry: ListUnit) {
    if (!armyList) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.removeListUnit(armyList.id, entry.id))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  if (loading) {
    return <p className="text-stone-600">Loading army list...</p>
  }

  if (!armyList) {
    return (
      <section>
        <Link className="text-sm font-semibold text-teal-700" to="/lists">
          Back to lists
        </Link>
        <p className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">
          {invalidListId ? 'Army list not found.' : (error ?? 'Army list not found.')}
        </p>
      </section>
    )
  }

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link className="text-sm font-semibold text-teal-700" to="/lists">
            Back to lists
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-stone-950">{armyList.name}</h1>
        </div>
      </div>
      {error ? <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p> : null}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
        <div>
          <h2 className="mb-3 text-xl font-semibold text-stone-950">Available units</h2>
          <div className="grid gap-4">
            {units.map((unit) => (
              <UnitCard key={unit.id} onAdd={addUnit} unit={unit} />
            ))}
          </div>
        </div>
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <PointTracker pointLimit={armyList.point_limit} totalPoints={armyList.total_points} />
          <div className="mt-4 rounded-md border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-xl font-semibold text-stone-950">Selected units</h2>
            <div className="mt-4 grid gap-3">
              {armyList.units.length === 0 ? (
                <p className="text-sm text-stone-600">No units added yet.</p>
              ) : null}
              {armyList.units.map((entry) => (
                <ListUnitRow
                  busy={busyUnitId === entry.unit}
                  entry={entry}
                  key={entry.id}
                  onDecrease={() => updateModelCount(entry, entry.model_count - 1)}
                  onIncrease={() => updateModelCount(entry, entry.model_count + 1)}
                  onRemove={() => removeUnit(entry)}
                  unit={unitLookup.get(entry.unit)}
                  factionId={armyList.faction}
                />
              ))}
            </div>
          </div>
        </aside>
      </div>
    </section>
  )
}

type ListUnitRowProps = {
  busy: boolean
  entry: ListUnit
  factionId: number
  unit?: Unit
  onDecrease: () => void
  onIncrease: () => void
  onRemove: () => void
}

function ListUnitRow({ busy, entry, factionId, onDecrease, onIncrease, onRemove, unit }: ListUnitRowProps) {
  const selectedSlot =
    unit?.weapon_slots.find((slot) => slot.id === entry.selected_weapon_slot) ??
    unit?.weapon_slots.find((slot) => slot.is_default) ??
    unit?.weapon_slots[0]
  const calcHref = selectedSlot
    ? `/calc?factionId=${factionId}&unitId=${entry.unit}&weaponId=${selectedSlot.weapon.id}`
    : null

  return (
    <article className="rounded border border-stone-200 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-stone-950">{entry.unit_name}</h3>
          <p className="text-sm text-stone-600">
            {entry.total_points.toLocaleString()} pts · {entry.selected_weapon_name ?? 'Default weapons'}
          </p>
          {unit ? (
            <p className="mt-1 text-xs text-stone-500">
              QU{unit.quality}+ DE{unit.defense}+ T{unit.tough}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {calcHref ? (
            <Link
              className="rounded border border-teal-300 px-2 py-1 text-sm font-semibold text-teal-700 hover:bg-teal-50"
              to={calcHref}
            >
              Calculate {entry.unit_name}
            </Link>
          ) : null}
          <button
            className="rounded border border-stone-300 px-2 py-1 text-sm font-semibold text-stone-700 hover:bg-stone-100"
            disabled={busy}
            onClick={onRemove}
            type="button"
          >
            Remove {entry.unit_name}
          </button>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <button
          aria-label={`Decrease ${entry.unit_name}`}
          className="h-8 w-8 rounded border border-stone-300 text-lg font-semibold disabled:opacity-40"
          disabled={busy || entry.model_count <= 1}
          onClick={onDecrease}
          type="button"
        >
          -
        </button>
        <span className="min-w-10 text-center font-semibold">{entry.model_count}</span>
        <button
          aria-label={`Increase ${entry.unit_name}`}
          className="h-8 w-8 rounded border border-stone-300 text-lg font-semibold disabled:opacity-40"
          disabled={busy}
          onClick={onIncrease}
          type="button"
        >
          +
        </button>
      </div>
    </article>
  )
}
