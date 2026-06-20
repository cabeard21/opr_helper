import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { ArmyList, ListAnalysisResult, ListAnalysisUnit, ListUnit, TargetProfile, Unit } from '../api/types'
import { PointTracker } from '../components/PointTracker'
import { UnitCard } from '../components/UnitCard'

const TARGET_PROFILES: TargetProfile[] = [
  { id: 'infantry', name: 'Infantry', defense: 5, tough: 1 },
  { id: 'elite', name: 'Elite', defense: 3, tough: 3 },
  { id: 'monster', name: 'Monster', defense: 2, tough: 10 },
]

export function ListBuilderPage() {
  const { id } = useParams()
  const listId = Number(id)
  const invalidListId = !Number.isFinite(listId) || listId <= 0
  const [armyList, setArmyList] = useState<ArmyList | null>(null)
  const [units, setUnits] = useState<Unit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!invalidListId)
  const [busyUnitId, setBusyUnitId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'builder' | 'analysis'>('builder')
  const [analysis, setAnalysis] = useState<ListAnalysisResult | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [exportMessage, setExportMessage] = useState('')

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

  async function loadAnalysis() {
    if (!armyList || analysisLoading) {
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

  async function exportArmyForge() {
    if (!armyList) {
      return
    }
    setError(null)
    setExportMessage('')
    try {
      const payload = await apiClient.exportArmyForgeList(armyList.id)
      const fileName = `${armyList.name.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'army-list'}-army-forge.json`
      const json = JSON.stringify(payload, null, 2)
      if (typeof Blob !== 'undefined' && typeof URL !== 'undefined' && URL.createObjectURL) {
        const url = URL.createObjectURL(new Blob([json], { type: 'application/json' }))
        const anchor = document.createElement('a')
        anchor.href = url
        anchor.download = fileName
        anchor.click()
        URL.revokeObjectURL(url)
      }
      setExportMessage(`Exported ${fileName}`)
    } catch (err) {
      setError((err as Error).message)
    }
  }

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

  async function updateSelectedWeapon(entry: ListUnit, nextSlotId: number | null) {
    if (!armyList) {
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

  async function updateSelectedUpgrades(entry: ListUnit, nextOptionIds: number[]) {
    if (!armyList) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(armyList.id, entry.id, { selected_upgrades: nextOptionIds }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function updateCombinedCount(entry: ListUnit, nextCount: number) {
    if (!armyList || nextCount < 1) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(armyList.id, entry.id, { combined_from_count: nextCount }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function updateParentEntry(entry: ListUnit, parentEntryId: number | null) {
    if (!armyList) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(armyList.id, entry.id, { parent_entry: parentEntryId }))
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
    return <p className="app-muted">Loading army list...</p>
  }

  if (!armyList) {
    return (
      <section>
        <Link className="app-link" to="/lists">
          Back to lists
        </Link>
        <p className="app-alert-danger mt-4">
          {invalidListId ? 'Army list not found.' : (error ?? 'Army list not found.')}
        </p>
      </section>
    )
  }

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link className="app-link" to="/lists">
            Back to lists
          </Link>
          <h1 className="app-heading mt-2">{armyList.name}</h1>
        </div>
        <div className="flex flex-wrap gap-2 rounded-md border p-1" style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
          <button
            className={activeTab === 'builder' ? 'app-button-primary px-3' : 'app-button-secondary px-3'}
            onClick={() => setActiveTab('builder')}
            type="button"
          >
            Builder
          </button>
          <button
            className={activeTab === 'analysis' ? 'app-button-primary px-3' : 'app-button-secondary px-3'}
            onClick={loadAnalysis}
            type="button"
          >
            Analysis
          </button>
          <button
            className="app-button-accent"
            onClick={exportArmyForge}
            type="button"
          >
            Export Army Forge
          </button>
        </div>
      </div>
      {error ? <p className="app-alert-danger mb-4">{error}</p> : null}
      {exportMessage ? <p className="app-alert-warning mb-4 text-sm">{exportMessage}</p> : null}
      <AdvisorListSummary armyList={armyList} />
      {activeTab === 'analysis' ? (
        <AnalysisPanel analysis={analysis} loading={analysisLoading} />
      ) : (
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
        <div>
          <h2 className="app-subheading mb-3">Available units</h2>
          <div className="grid gap-4">
            {units.map((unit) => (
              <UnitCard key={unit.id} onAdd={addUnit} unit={unit} />
            ))}
          </div>
        </div>
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <PointTracker pointLimit={armyList.point_limit} totalPoints={armyList.total_points} />
          <ListValidationMessages validation={armyList.validation} />
          <div className="app-card mt-4">
            <h2 className="app-subheading">Selected units</h2>
            <div className="mt-4 grid gap-3">
              {armyList.units.length === 0 ? (
                <p className="app-muted text-sm">No units added yet.</p>
              ) : null}
              {armyList.units.map((entry) => (
                <ListUnitRow
                  busy={busyUnitId === entry.unit}
                  entry={entry}
                  key={entry.id}
                  onDecrease={() => updateModelCount(entry, entry.model_count - 1)}
                  onCombineDecrease={() => updateCombinedCount(entry, entry.combined_from_count - 1)}
                  onCombineIncrease={() => updateCombinedCount(entry, entry.combined_from_count + 1)}
                  onIncrease={() => updateModelCount(entry, entry.model_count + 1)}
                  onParentChange={(parentEntryId) => updateParentEntry(entry, parentEntryId)}
                  onRemove={() => removeUnit(entry)}
                  onSelectWeapon={(slotId) => updateSelectedWeapon(entry, slotId)}
                  onSelectUpgrades={(optionIds) => updateSelectedUpgrades(entry, optionIds)}
                  unit={unitLookup.get(entry.unit)}
                  armyUnits={armyList.units}
                  unitLookup={unitLookup}
                  factionId={armyList.faction}
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
  armyUnits: ListUnit[]
  unitLookup: Map<number, Unit>
  onDecrease: () => void
  onCombineDecrease: () => void
  onCombineIncrease: () => void
  onIncrease: () => void
  onParentChange: (parentEntryId: number | null) => void
  onRemove: () => void
  onSelectWeapon: (slotId: number | null) => void
  onSelectUpgrades: (optionIds: number[]) => void
}

function ListUnitRow({
  armyUnits,
  busy,
  entry,
  factionId,
  onCombineDecrease,
  onCombineIncrease,
  onDecrease,
  onIncrease,
  onParentChange,
  onRemove,
  onSelectWeapon,
  onSelectUpgrades,
  unit,
  unitLookup,
}: ListUnitRowProps) {
  const selectedSlot =
    unit?.weapon_slots.find((slot) => slot.id === entry.selected_weapon_slot) ??
    unit?.weapon_slots.find((slot) => slot.is_default) ??
    unit?.weapon_slots[0]
  const calcHref = selectedSlot
    ? `/calc?factionId=${factionId}&unitId=${entry.unit}&weaponId=${selectedSlot.weapon.id}`
    : null
  const hasNativeUpgradeSections = (unit?.upgrade_sections.length ?? 0) > 0

  return (
    <article className="rounded border p-3" style={{ borderColor: 'var(--color-border)' }}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>{entry.unit_name}</h3>
          <p className="app-muted text-sm">
            {entry.total_points.toLocaleString()} pts - {entry.selected_weapon_name ?? 'Default weapons'}
          </p>
          {entry.loadout_summary ? (
            <p className="app-muted text-sm">{entry.loadout_summary}</p>
          ) : null}
          {unit ? (
            <p className="app-subtle mt-1 text-xs">
              QU{unit.quality}+ DE{unit.defense}+ T{unit.tough}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {calcHref ? (
            <Link
              className="app-button-accent px-2 py-1"
              to={calcHref}
            >
              Calculate {entry.unit_name}
            </Link>
          ) : null}
          <button
            className="app-button-secondary px-2 py-1"
            disabled={busy}
            onClick={onRemove}
            type="button"
          >
            Remove {entry.unit_name}
          </button>
        </div>
      </div>
      <div className="mt-3 grid gap-3">
          {unit && hasNativeUpgradeSections ? (
            <div className="grid gap-2">
              {unit.upgrade_sections.map((section) => {
                const selectedOption =
                  section.options.find((option) => entry.selected_upgrades.includes(option.id)) ?? null
                return (
                  <label className="app-label grid gap-1" key={section.id}>
                    {section.label}
                    <select
                      aria-label={`${section.label} for ${entry.unit_name}`}
                      className="app-field"
                      disabled={busy}
                      onChange={(event) => {
                        const optionId = event.target.value ? Number(event.target.value) : null
                        const sectionOptionIds = new Set(section.options.map((option) => option.id))
                        const nextOptionIds = entry.selected_upgrades.filter((id) => !sectionOptionIds.has(id))
                        onSelectUpgrades(optionId ? [...nextOptionIds, optionId] : nextOptionIds)
                      }}
                      value={selectedOption?.id ?? ''}
                    >
                      <option value="">No upgrade</option>
                      {section.options.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                          {option.cost > 0 ? ` (+${option.cost} pts)` : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                )
              })}
            </div>
          ) : unit && unit.weapon_slots.length > 0 ? (
            <label className="app-label grid gap-1">
              Weapon for {entry.unit_name}
              <select
                aria-label={`Weapon for ${entry.unit_name}`}
                className="app-field"
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
              className="h-8 w-8 rounded border text-lg font-semibold disabled:opacity-40"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
              disabled={busy || entry.model_count <= (unit?.min_models ?? 1)}
              onClick={onDecrease}
              type="button"
            >
              -
            </button>
            <span className="min-w-10 text-center font-semibold">{entry.model_count}</span>
            <button
              aria-label={`Increase ${entry.unit_name}`}
              className="h-8 w-8 rounded border text-lg font-semibold disabled:opacity-40"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
              disabled={busy || (unit?.max_models !== null && unit?.max_models !== undefined && entry.model_count >= unit.max_models)}
              onClick={onIncrease}
              type="button"
            >
              +
            </button>
          </div>
          {unit && entry.model_count > 1 ? (
            <div className="flex items-center gap-2">
              <span className="app-label">Combined copies</span>
              <button
                aria-label={`Decrease combined ${entry.unit_name}`}
                className="h-8 w-8 rounded border text-lg font-semibold disabled:opacity-40"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                disabled={busy || entry.combined_from_count <= 1}
                onClick={onCombineDecrease}
                type="button"
              >
                -
              </button>
              <span className="min-w-10 text-center font-semibold">{entry.combined_from_count}</span>
              <button
                aria-label={`Increase combined ${entry.unit_name}`}
                className="h-8 w-8 rounded border text-lg font-semibold disabled:opacity-40"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                disabled={busy}
                onClick={onCombineIncrease}
                type="button"
              >
                +
              </button>
            </div>
          ) : null}
          {unit && isHero(unit) ? (
            <label className="app-label grid gap-1">
              Embed {entry.unit_name}
              <select
                aria-label={`Embed ${entry.unit_name}`}
                className="app-field"
                disabled={busy}
                onChange={(event) => onParentChange(event.target.value ? Number(event.target.value) : null)}
                value={entry.parent_entry ?? ''}
              >
                <option value="">No host unit</option>
                {armyUnits
                  .filter((candidate) => candidate.id !== entry.id && !candidate.parent_entry)
                  .filter((candidate) => {
                    const candidateUnit = unitLookup.get(candidate.unit)
                    return candidate.model_count > 1 && candidateUnit && !isHero(candidateUnit)
                  })
                  .map((candidate) => (
                    <option key={candidate.id} value={candidate.id}>
                      {candidate.unit_name}
                    </option>
                  ))}
              </select>
            </label>
          ) : null}
      </div>
    </article>
  )
}

function AdvisorListSummary({ armyList }: { armyList: ArmyList }) {
  if (!armyList.advisor_archetype && !armyList.advisor_strategy_summary) {
    return null
  }

  return (
    <section className="app-card mb-6">
      <div>
        <h2 className="app-subheading">{armyList.advisor_archetype || 'Advisor summary'}</h2>
        {armyList.advisor_playstyle ? (
          <p className="mt-1 text-sm font-semibold" style={{ color: 'var(--color-accent)' }}>
            {armyList.advisor_playstyle}
          </p>
        ) : null}
      </div>
      {armyList.advisor_strategy_summary ? (
        <p className="app-muted mt-3 text-sm leading-6">{armyList.advisor_strategy_summary}</p>
      ) : null}
      {armyList.advisor_warnings.length > 0 ? (
        <div className="app-alert-warning mt-3 text-sm">
          {armyList.advisor_warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}
    </section>
  )
}

function isHero(unit: Unit) {
  return Object.keys(unit.special_rules).some((rule) => rule.toLowerCase() === 'hero')
}

function ListValidationMessages({ validation }: { validation?: ArmyList['validation'] }) {
  const messages = [...(validation?.errors ?? []), ...(validation?.warnings ?? [])]
  if (messages.length === 0) {
    return null
  }

  return (
    <div className="app-alert-warning mt-3 text-sm">
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

type AnalysisSort =
  | { kind: 'unit' | 'durability'; direction: 'asc' | 'desc' }
  | { kind: 'ev' | 'efficiency'; targetId: string; direction: 'asc' | 'desc' }

function AnalysisPanel({ analysis, loading }: AnalysisPanelProps) {
  const [selectedTargetId, setSelectedTargetId] = useState(TARGET_PROFILES[0].id)
  const [sort, setSort] = useState<AnalysisSort>({
    kind: 'efficiency',
    targetId: TARGET_PROFILES[0].id,
    direction: 'desc',
  })

  if (loading) {
    return <p className="app-card app-muted">Loading analysis...</p>
  }

  if (!analysis) {
    return <p className="app-card app-muted">No analysis loaded yet.</p>
  }

  const selectedTarget = analysis.targets.find((target) => target.id === selectedTargetId) ?? analysis.targets[0]
  const rankedUnits = [...analysis.units].sort(
    (left, right) => resultFor(right, selectedTarget.id).wounds_per_100_points - resultFor(left, selectedTarget.id).wounds_per_100_points,
  )
  const tableUnits = sortedAnalysisUnits(analysis.units, sort)

  function updateSort(nextSort: AnalysisSort) {
    setSort((current) => {
      if (sameSortColumn(current, nextSort)) {
        return {
          ...current,
          direction: current.direction === 'asc' ? 'desc' : 'asc',
        } as AnalysisSort
      }
      return nextSort
    })
  }

  return (
    <section className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="app-section-heading">Army analysis</h2>
          <p className="app-muted mt-1 text-sm">Expected wounds and efficiency by target profile.</p>
        </div>
        <label className="app-label grid gap-1">
          Army vs target
          <select
            className="app-field"
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

      <div className="app-card">
        <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Army vs {selectedTarget.name}</h3>
        <div className="mt-4 grid gap-3">
          {rankedUnits.map((unit) => {
            const result = resultFor(unit, selectedTarget.id)
            return (
              <div key={unit.list_unit_id}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-semibold" style={{ color: 'var(--color-text)' }}>{unit.unit_name}</span>
                  <span className="app-muted">{result.ev.toFixed(2)} EV</span>
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded" style={{ background: 'var(--color-bg-soft)' }}>
                  <div
                    className="h-full"
                    style={{
                      background: 'var(--color-accent)',
                      width: `${Math.min(100, result.wounds_per_100_points * 30)}%`,
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border shadow-sm" style={{ background: 'var(--color-surface-raised)', borderColor: 'var(--color-border)' }}>
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead className="text-left" style={{ background: 'var(--color-bg-soft)', color: 'var(--color-text-muted)' }}>
            <tr>
              <SortableHeader
                active={sort.kind === 'unit'}
                direction={sort.direction}
                label="Unit"
                onClick={() => updateSort({ kind: 'unit', direction: 'asc' })}
              />
              <SortableHeader
                active={sort.kind === 'durability'}
                direction={sort.direction}
                label="Effective wounds / 100 pts"
                onClick={() => updateSort({ kind: 'durability', direction: 'desc' })}
              />
              {analysis.targets.map((target) => (
                <th className="px-4 py-3 font-semibold" key={target.id}>
                  <div className="grid gap-1">
                    <span>{target.name}</span>
                    <div className="flex flex-wrap gap-2">
                      <SortableButton
                        active={sort.kind === 'ev' && sort.targetId === target.id}
                        direction={sort.direction}
                        label={`${target.name} EV`}
                        onClick={() => updateSort({ kind: 'ev', targetId: target.id, direction: 'desc' })}
                      />
                      <SortableButton
                        active={sort.kind === 'efficiency' && sort.targetId === target.id}
                        direction={sort.direction}
                        label={`${target.name} wounds / 100 pts`}
                        onClick={() => updateSort({ kind: 'efficiency', targetId: target.id, direction: 'desc' })}
                      />
                    </div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableUnits.map((unit) => (
              <tr className="border-t" key={unit.list_unit_id} style={{ borderColor: 'var(--color-border)' }}>
                <td className="px-4 py-3 font-semibold" style={{ color: 'var(--color-text)' }}>{unit.unit_name}</td>
                <td className="px-4 py-3" style={{ color: 'var(--color-text-muted)' }}>
                  {unit.effective_wounds_per_100_points.toFixed(2)}
                </td>
                {analysis.targets.map((target) => {
                  const result = resultFor(unit, target.id)
                  return (
                    <td className="px-4 py-3" key={target.id} style={{ color: 'var(--color-text-muted)' }}>
                      <div className="font-semibold" style={{ color: 'var(--color-text)' }}>
                        {result.ev.toFixed(2)} EV
                      </div>
                      <div className="app-muted mt-1 text-xs">
                        {result.wounds_per_100_points.toFixed(2)} wounds / 100 pts
                      </div>
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

function SortableHeader({
  active,
  direction,
  label,
  onClick,
}: {
  active: boolean
  direction: 'asc' | 'desc'
  label: string
  onClick: () => void
}) {
  return (
    <th aria-sort={active ? (direction === 'asc' ? 'ascending' : 'descending') : 'none'} className="px-4 py-3 font-semibold">
      <button
        className="text-left font-semibold"
        onClick={onClick}
        style={{ color: 'inherit' }}
        type="button"
      >
        {label}{active ? (direction === 'asc' ? ' ^' : ' v') : ''}
      </button>
    </th>
  )
}

function SortableButton({
  active,
  direction,
  label,
  onClick,
}: {
  active: boolean
  direction: 'asc' | 'desc'
  label: string
  onClick: () => void
}) {
  return (
    <button
      aria-pressed={active}
      className="text-left text-xs font-semibold"
      onClick={onClick}
      style={{ color: 'inherit' }}
      type="button"
    >
      {label}{active ? (direction === 'asc' ? ' ^' : ' v') : ''}
    </button>
  )
}

function sortedAnalysisUnits(units: ListAnalysisUnit[], sort: AnalysisSort) {
  return [...units].sort((left, right) => {
    const direction = sort.direction === 'asc' ? 1 : -1
    if (sort.kind === 'unit') {
      return direction * left.unit_name.localeCompare(right.unit_name)
    }
    if (sort.kind === 'durability') {
      const leftValue = left.effective_wounds_per_100_points
      const rightValue = right.effective_wounds_per_100_points
      if (leftValue === rightValue) {
        return left.unit_name.localeCompare(right.unit_name)
      }
      return direction * (leftValue - rightValue)
    }

    if (!isTargetSort(sort)) {
      return 0
    }
    const leftResult = resultFor(left, sort.targetId)
    const rightResult = resultFor(right, sort.targetId)
    const leftValue = sort.kind === 'ev' ? leftResult.ev : leftResult.wounds_per_100_points
    const rightValue = sort.kind === 'ev' ? rightResult.ev : rightResult.wounds_per_100_points
    if (leftValue === rightValue) {
      return left.unit_name.localeCompare(right.unit_name)
    }
    return direction * (leftValue - rightValue)
  })
}

function sameSortColumn(left: AnalysisSort, right: AnalysisSort) {
  if (left.kind !== right.kind) {
    return false
  }
  if (left.kind === 'unit' || left.kind === 'durability' || right.kind === 'unit' || right.kind === 'durability') {
    return true
  }
  return isTargetSort(left) && isTargetSort(right) && left.targetId === right.targetId
}

function isTargetSort(sort: AnalysisSort): sort is Extract<AnalysisSort, { targetId: string }> {
  return sort.kind === 'ev' || sort.kind === 'efficiency'
}

function BestUnitCard({ analysis, target }: { analysis: ListAnalysisResult; target: TargetProfile }) {
  const bestUnit = [...analysis.units].sort(
    (left, right) => resultFor(right, target.id).wounds_per_100_points - resultFor(left, target.id).wounds_per_100_points,
  )[0]
  const total = analysis.totals.find((candidate) => candidate.target_id === target.id)

  return (
    <article className="app-card">
      <h3 className="app-subtle text-sm font-semibold uppercase">Best vs {target.name}</h3>
      <p className="mt-2 text-lg font-semibold" style={{ color: 'var(--color-text)' }}>{bestUnit?.unit_name ?? 'No units'}</p>
      <p className="app-muted mt-1 text-sm">
        {bestUnit ? `${resultFor(bestUnit, target.id).wounds_per_100_points.toFixed(2)} wounds / 100 pts` : 'Add units to compare'}
      </p>
      <p className="app-subtle mt-3 text-xs font-semibold">
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
