import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { ArmyList, ListAnalysisResult, ListAnalysisUnit, ListUnit, TargetProfile, Unit } from '../api/types'
import { PointTracker } from '../components/PointTracker'
import { UnitCard } from '../components/UnitCard'

const TARGET_PROFILES: TargetProfile[] = [
  { id: 'infantry', name: 'Infantry', defense: 5, tough: 1 },
  { id: 'elite', name: 'Elite', defense: 3, tough: 3 },
  { id: 'monster', name: 'Monster', defense: 2, tough: 10 },
]

type ShareSnapshot = {
  armyList: ArmyList
  units: Unit[]
}

export function ListBuilderPage() {
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const sharedSnapshot = useMemo(() => decodeShareSnapshot(searchParams.get('share')), [searchParams])
  const listId = Number(id)
  const readOnly = Boolean(sharedSnapshot)
  const invalidListId = !readOnly && (!Number.isFinite(listId) || listId <= 0)
  const [armyList, setArmyList] = useState<ArmyList | null>(sharedSnapshot?.armyList ?? null)
  const [units, setUnits] = useState<Unit[]>(sharedSnapshot?.units ?? [])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!invalidListId && !readOnly)
  const [busyUnitId, setBusyUnitId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'builder' | 'analysis'>('builder')
  const [analysis, setAnalysis] = useState<ListAnalysisResult | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [shareUrl, setShareUrl] = useState('')

  useEffect(() => {
    if (invalidListId || readOnly) {
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
  }, [listId, invalidListId, readOnly])

  const unitLookup = useMemo(() => new Map(units.map((unit) => [unit.id, unit])), [units])

  async function loadAnalysis() {
    if (!armyList || readOnly || analysisLoading) {
      return
    }
    setActiveTab('analysis')
    if (analysis) {
      return
    }
    setAnalysisLoading(true)
    setError(null)
    try {
      setAnalysis(await apiClient.analyzeList(armyList.id, TARGET_PROFILES))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setAnalysisLoading(false)
    }
  }

  function createShareLink() {
    if (!armyList) {
      return
    }
    const share = encodeShareSnapshot({ armyList, units })
    setShareUrl(`${window.location.origin}/lists/shared?share=${share}`)
  }

  async function addUnit(unit: Unit) {
    if (!armyList || readOnly) {
      return
    }
    const defaultSlot = unit.weapon_slots.find((slot) => slot.is_default) ?? unit.weapon_slots[0]
    setBusyUnitId(unit.id)
    setError(null)
    try {
      setArmyList(
        await apiClient.addListUnit(armyList.id, {
          unit: unit.id,
          model_count: unit.default_models,
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
    if (!armyList || readOnly || nextCount < 1) {
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

  async function updateSelectedWeapon(entry: ListUnit, nextSlotId: number | null) {
    if (!armyList || readOnly) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(armyList.id, entry.id, { selected_weapon_slot: nextSlotId }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function removeUnit(entry: ListUnit) {
    if (!armyList || readOnly) {
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
          {readOnly ? <p className="mt-1 text-sm font-semibold text-stone-600">Read-only shared list</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className={`rounded border px-3 py-2 text-sm font-semibold ${
              activeTab === 'builder' ? 'border-stone-950 bg-stone-950 text-white' : 'border-stone-300 text-stone-700'
            }`}
            onClick={() => setActiveTab('builder')}
            type="button"
          >
            Builder
          </button>
          {!readOnly ? (
            <button
              className={`rounded border px-3 py-2 text-sm font-semibold ${
                activeTab === 'analysis' ? 'border-stone-950 bg-stone-950 text-white' : 'border-stone-300 text-stone-700'
              }`}
              onClick={loadAnalysis}
              type="button"
            >
              Analysis
            </button>
          ) : null}
          <button
            className="rounded border border-teal-300 px-3 py-2 text-sm font-semibold text-teal-700 hover:bg-teal-50"
            onClick={createShareLink}
            type="button"
          >
            Create share link
          </button>
        </div>
      </div>
      {error ? <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p> : null}
      {shareUrl ? (
        <label className="mb-4 grid gap-1 text-sm font-semibold text-stone-700">
          Share URL
          <input
            aria-label="Share URL"
            className="rounded border border-stone-300 px-3 py-2 font-normal text-stone-950"
            readOnly
            value={shareUrl}
          />
        </label>
      ) : null}
      {activeTab === 'analysis' ? (
        <AnalysisPanel analysis={analysis} loading={analysisLoading} />
      ) : (
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
        <div>
          <h2 className="mb-3 text-xl font-semibold text-stone-950">Available units</h2>
          <div className="grid gap-4">
            {units.map((unit) => (
              <UnitCard key={unit.id} onAdd={readOnly ? undefined : addUnit} unit={unit} />
            ))}
          </div>
        </div>
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <PointTracker pointLimit={armyList.point_limit} totalPoints={armyList.total_points} />
          <ListValidationMessages validation={armyList.validation} />
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
                  onSelectWeapon={(slotId) => updateSelectedWeapon(entry, slotId)}
                  unit={unitLookup.get(entry.unit)}
                  factionId={armyList.faction}
                  readOnly={readOnly}
                />
              ))}
            </div>
          </div>
        </aside>
      </div>
      )}
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
  onSelectWeapon: (slotId: number | null) => void
  readOnly: boolean
}

function ListUnitRow({ busy, entry, factionId, onDecrease, onIncrease, onRemove, onSelectWeapon, readOnly, unit }: ListUnitRowProps) {
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
          {!readOnly ? (
            <button
              className="rounded border border-stone-300 px-2 py-1 text-sm font-semibold text-stone-700 hover:bg-stone-100"
              disabled={busy}
              onClick={onRemove}
              type="button"
            >
              Remove {entry.unit_name}
            </button>
          ) : null}
        </div>
      </div>
      {!readOnly ? (
        <div className="mt-3 grid gap-3">
          {unit && unit.weapon_slots.length > 0 ? (
            <label className="grid gap-1 text-sm font-semibold text-stone-700">
              Weapon for {entry.unit_name}
              <select
                aria-label={`Weapon for ${entry.unit_name}`}
                className="rounded border border-stone-300 px-3 py-2 font-normal text-stone-950"
                disabled={busy}
                onChange={(event) => onSelectWeapon(Number(event.target.value))}
                value={selectedSlot?.id ?? ''}
              >
                {unit.weapon_slots.map((slot) => (
                  <option key={slot.id} value={slot.id}>
                    {slot.weapon.name}
                    {slot.upgrade_cost > 0 ? ` (+${slot.upgrade_cost} pts)` : ''}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <div className="flex items-center gap-2">
            <button
              aria-label={`Decrease ${entry.unit_name}`}
              className="h-8 w-8 rounded border border-stone-300 text-lg font-semibold disabled:opacity-40"
              disabled={busy || entry.model_count <= (unit?.min_models ?? 1)}
              onClick={onDecrease}
              type="button"
            >
              -
            </button>
            <span className="min-w-10 text-center font-semibold">{entry.model_count}</span>
            <button
              aria-label={`Increase ${entry.unit_name}`}
              className="h-8 w-8 rounded border border-stone-300 text-lg font-semibold disabled:opacity-40"
              disabled={busy || (unit?.max_models !== null && unit?.max_models !== undefined && entry.model_count >= unit.max_models)}
              onClick={onIncrease}
              type="button"
            >
              +
            </button>
          </div>
        </div>
      ) : null}
    </article>
  )
}

function ListValidationMessages({ validation }: { validation?: ArmyList['validation'] }) {
  const messages = [...(validation?.errors ?? []), ...(validation?.warnings ?? [])]
  if (messages.length === 0) {
    return null
  }

  return (
    <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
      {messages.map((message) => (
        <p key={`${message.code}-${message.list_unit_id ?? 'list'}`}>{message.message}</p>
      ))}
    </div>
  )
}

type AnalysisPanelProps = {
  analysis: ListAnalysisResult | null
  loading: boolean
}

function AnalysisPanel({ analysis, loading }: AnalysisPanelProps) {
  const [selectedTargetId, setSelectedTargetId] = useState(TARGET_PROFILES[0].id)

  if (loading) {
    return <p className="rounded border border-stone-200 bg-white p-4 text-stone-600">Loading analysis...</p>
  }

  if (!analysis) {
    return <p className="rounded border border-stone-200 bg-white p-4 text-stone-600">No analysis loaded yet.</p>
  }

  const selectedTarget = analysis.targets.find((target) => target.id === selectedTargetId) ?? analysis.targets[0]
  const rankedUnits = [...analysis.units].sort(
    (left, right) => resultFor(right, selectedTarget.id).wounds_per_100_points - resultFor(left, selectedTarget.id).wounds_per_100_points,
  )

  return (
    <section className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-stone-950">Army analysis</h2>
          <p className="mt-1 text-sm text-stone-600">Expected wounds and efficiency by target profile.</p>
        </div>
        <label className="grid gap-1 text-sm font-semibold text-stone-700">
          Army vs target
          <select
            className="rounded border border-stone-300 px-3 py-2 font-normal text-stone-950"
            onChange={(event) => setSelectedTargetId(event.target.value)}
            value={selectedTarget.id}
          >
            {analysis.targets.map((target) => (
              <option key={target.id} value={target.id}>
                {target.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {analysis.targets.map((target) => (
          <BestUnitCard analysis={analysis} key={target.id} target={target} />
        ))}
      </div>

      <div className="rounded-md border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-stone-950">Army vs {selectedTarget.name}</h3>
        <div className="mt-4 grid gap-3">
          {rankedUnits.map((unit) => {
            const result = resultFor(unit, selectedTarget.id)
            return (
              <div key={unit.list_unit_id}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-semibold text-stone-800">{unit.unit_name}</span>
                  <span className="text-stone-600">{result.ev.toFixed(2)} EV</span>
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded bg-stone-200">
                  <div
                    className="h-full bg-teal-700"
                    style={{ width: `${Math.min(100, result.wounds_per_100_points * 30)}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border border-stone-200 bg-white shadow-sm">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead className="bg-stone-100 text-left text-stone-700">
            <tr>
              <th className="px-4 py-3 font-semibold">Unit</th>
              {analysis.targets.map((target) => (
                <th className="px-4 py-3 font-semibold" key={target.id}>
                  {target.name} EV
                </th>
              ))}
              {analysis.targets.map((target) => (
                <th className="px-4 py-3 font-semibold" key={`${target.id}-efficiency`}>
                  {target.name} / 100 pts
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {analysis.units.map((unit) => (
              <tr className="border-t border-stone-200" key={unit.list_unit_id}>
                <td className="px-4 py-3 font-semibold text-stone-900">{unit.unit_name}</td>
                {analysis.targets.map((target) => {
                  const result = resultFor(unit, target.id)
                  return (
                    <td className="px-4 py-3 text-stone-700" key={target.id}>
                      {result.ev.toFixed(2)}
                    </td>
                  )
                })}
                {analysis.targets.map((target) => {
                  const result = resultFor(unit, target.id)
                  return (
                    <td className="px-4 py-3 text-stone-700" key={`${target.id}-efficiency`}>
                      {result.wounds_per_100_points.toFixed(2)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function BestUnitCard({ analysis, target }: { analysis: ListAnalysisResult; target: TargetProfile }) {
  const bestUnit = [...analysis.units].sort(
    (left, right) => resultFor(right, target.id).wounds_per_100_points - resultFor(left, target.id).wounds_per_100_points,
  )[0]
  const total = analysis.totals.find((candidate) => candidate.target_id === target.id)

  return (
    <article className="rounded-md border border-stone-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold uppercase text-stone-500">Best vs {target.name}</h3>
      <p className="mt-2 text-lg font-semibold text-stone-950">{bestUnit?.unit_name ?? 'No units'}</p>
      <p className="mt-1 text-sm text-stone-600">
        {bestUnit ? `${resultFor(bestUnit, target.id).wounds_per_100_points.toFixed(2)} wounds / 100 pts` : 'Add units to compare'}
      </p>
      <p className="mt-3 text-xs font-semibold text-stone-500">
        {total ? `${total.ev.toFixed(2)} total EV` : '0.00 total EV'}
      </p>
    </article>
  )
}

function resultFor(unit: ListAnalysisUnit, targetId: string) {
  return (
    unit.target_results.find((result) => result.target_id === targetId) ?? {
      target_id: targetId,
      ev: 0,
      wounds_per_100_points: 0,
      p_kill_model: 0,
    }
  )
}

function encodeShareSnapshot(snapshot: ShareSnapshot): string {
  return btoa(encodeURIComponent(JSON.stringify(snapshot)))
}

function decodeShareSnapshot(value: string | null): ShareSnapshot | null {
  if (!value) {
    return null
  }
  try {
    const parsed = JSON.parse(decodeURIComponent(atob(value))) as ShareSnapshot
    if (!parsed.armyList || !Array.isArray(parsed.units)) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}
