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

const EMPTY_UNITS: Unit[] = []

export function ListBuilderPage() {
  const { id } = useParams()
  const listId = Number(id)
  const invalidListId = !Number.isFinite(listId) || listId <= 0
  const [armyList, setArmyList] = useState<ArmyList | null>(null)
  const [units, setUnits] = useState<Unit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loadedListId, setLoadedListId] = useState<number | null>(null)
  const [errorListId, setErrorListId] = useState<number | null>(null)
  const [busyUnitId, setBusyUnitId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'builder' | 'analysis'>('builder')
  const [analysis, setAnalysis] = useState<ListAnalysisResult | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [exportMessage, setExportMessage] = useState('')

  useEffect(() => {
    let active = true

    if (invalidListId) {
      return () => {
        active = false
      }
    }

    apiClient
      .getList(listId)
      .then(async (list) => {
        const nextUnits = await apiClient.getFactionUnits(list.faction)
        if (active) {
          setArmyList(list)
          setUnits(nextUnits)
          setLoadedListId(listId)
          setError(null)
          setErrorListId(null)
          setBusyUnitId(null)
          setAnalysis(null)
          setAnalysisLoading(false)
          setExportMessage('')
        }
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message)
          setErrorListId(listId)
        }
      })

    return () => {
      active = false
    }
  }, [listId, invalidListId])

  const currentArmyList = loadedListId === listId ? armyList : null
  const currentUnits = loadedListId === listId ? units : EMPTY_UNITS
  const displayError = errorListId === null || errorListId === listId ? error : null
  const routeLoading = !invalidListId && loadedListId !== listId && errorListId !== listId
  const unitLookup = useMemo(() => new Map(currentUnits.map((unit) => [unit.id, unit])), [currentUnits])

  async function loadAnalysis() {
    if (!currentArmyList || analysisLoading) {
      return
    }
    setActiveTab('analysis')
    if (analysis) {
      return
    }
    setAnalysisLoading(true)
    setError(null)
    try {
      setAnalysis(await apiClient.analyzeList(currentArmyList.id, TARGET_PROFILES))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setAnalysisLoading(false)
    }
  }

  async function exportArmyForge() {
    if (!currentArmyList) {
      return
    }
    setError(null)
    setExportMessage('')
    try {
      const payload = await apiClient.exportArmyForgeList(currentArmyList.id)
      const fileName = `${currentArmyList.name.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'army-list'}-army-forge.json`
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
    if (!currentArmyList) {
      return
    }
    const defaultSlot = unit.weapon_slots.find((slot) => slot.is_default) ?? unit.weapon_slots[0]
    setBusyUnitId(unit.id)
    setError(null)
    try {
      setArmyList(
        await apiClient.addListUnit(currentArmyList.id, {
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
    if (!currentArmyList || nextCount < 1) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(currentArmyList.id, entry.id, { model_count: nextCount }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function updateSelectedWeapon(entry: ListUnit, nextSlotId: number | null) {
    if (!currentArmyList) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(currentArmyList.id, entry.id, { selected_weapon_slot: nextSlotId }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function updateSelectedUpgrades(entry: ListUnit, nextOptionIds: number[]) {
    if (!currentArmyList) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(currentArmyList.id, entry.id, { selected_upgrades: nextOptionIds }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function updateCombinedCount(entry: ListUnit, nextCount: number) {
    if (!currentArmyList || nextCount < 1) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(currentArmyList.id, entry.id, { combined_from_count: nextCount }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function updateParentEntry(entry: ListUnit, parentEntryId: number | null) {
    if (!currentArmyList) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.updateListUnit(currentArmyList.id, entry.id, { parent_entry: parentEntryId }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  async function removeUnit(entry: ListUnit) {
    if (!currentArmyList) {
      return
    }
    setBusyUnitId(entry.unit)
    setError(null)
    try {
      setArmyList(await apiClient.removeListUnit(currentArmyList.id, entry.id))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusyUnitId(null)
    }
  }

  if (routeLoading) {
    return <p className="app-muted">Loading army list...</p>
  }

  if (!currentArmyList) {
    return (
      <section>
        <Link className="app-link" to="/lists">
          Back to lists
        </Link>
        <p className="app-alert-danger mt-4">
          {invalidListId ? 'Army list not found.' : (displayError ?? 'Army list not found.')}
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
          <h1 className="app-heading mt-2">{currentArmyList.name}</h1>
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
      {displayError ? <p className="app-alert-danger mb-4">{displayError}</p> : null}
      {exportMessage ? <p className="app-alert-warning mb-4 text-sm">{exportMessage}</p> : null}
      <AdvisorListSummary armyList={currentArmyList} />
      {activeTab === 'analysis' ? (
        <AnalysisPanel analysis={analysis} armyList={currentArmyList} loading={analysisLoading} units={currentUnits} />
      ) : (
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
        <div>
          <h2 className="app-subheading mb-3">Available units</h2>
          <div className="grid gap-4">
            {currentUnits.map((unit) => (
              <UnitCard key={unit.id} onAdd={addUnit} unit={unit} />
            ))}
          </div>
        </div>
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <PointTracker pointLimit={currentArmyList.point_limit} totalPoints={currentArmyList.total_points} />
          <ListValidationMessages validation={currentArmyList.validation} />
          <div className="app-card mt-4">
            <h2 className="app-subheading">Selected units</h2>
            <div className="mt-4 grid gap-3">
              {currentArmyList.units.length === 0 ? (
                <p className="app-muted text-sm">No units added yet.</p>
              ) : null}
              {currentArmyList.units.map((entry) => (
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
                  armyUnits={currentArmyList.units}
                  unitLookup={unitLookup}
                  factionId={currentArmyList.faction}
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
    <article className="min-w-0 rounded border p-3" style={{ borderColor: 'var(--color-border)' }}>
      <div className="grid min-w-0 gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
        <div className="min-w-0">
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
        <div className="flex flex-wrap gap-2 sm:justify-end">
          {calcHref ? (
            <Link
              aria-label={`Calculate ${entry.unit_name}`}
              className="app-button-accent px-2 py-1"
              to={calcHref}
            >
              Calculate
            </Link>
          ) : null}
          <button
            aria-label={`Remove ${entry.unit_name}`}
            className="app-button-secondary px-2 py-1"
            disabled={busy}
            onClick={onRemove}
            type="button"
          >
            Remove
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
                      className="app-field min-w-0 w-full"
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
                className="app-field min-w-0 w-full"
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
                className="app-field min-w-0 w-full"
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
  armyList: ArmyList
  loading: boolean
  units: Unit[]
}

type AnalysisSort =
  | { kind: 'unit' | 'toughness' | 'durability'; direction: 'asc' | 'desc' }
  | { kind: 'ev' | 'efficiency'; targetId: string; direction: 'asc' | 'desc' }

type ListHealthMetric = {
  id: string
  label: string
  score: number
  status: 'Strong' | 'Watch' | 'Gap'
  summary: string
}

function AnalysisPanel({ analysis, armyList, loading, units }: AnalysisPanelProps) {
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
    (left, right) => resultFor(right, selectedTarget.id).ev - resultFor(left, selectedTarget.id).ev,
  )
  const toughnessUnits = [...analysis.units].sort((left, right) => right.effective_wounds - left.effective_wounds)
  const maxSelectedEv = Math.max(0, ...rankedUnits.map((unit) => resultFor(unit, selectedTarget.id).ev))
  const maxToughness = Math.max(0, ...toughnessUnits.map((unit) => unit.effective_wounds))
  const tableUnits = sortedAnalysisUnits(analysis.units, sort)
  const healthMetrics = buildListHealthMetrics(armyList, units, analysis)

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

      <ListHealthWeb metrics={healthMetrics} />

      <div className="grid gap-4 lg:grid-cols-3">
        {analysis.targets.map((target) => (
          <BestUnitCard analysis={analysis} key={target.id} target={target} />
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="app-card">
          <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Army vs {selectedTarget.name}</h3>
          <div className="mt-4 grid gap-3">
            {rankedUnits.map((unit) => {
              const result = resultFor(unit, selectedTarget.id)
              return (
                <AnalysisBar
                  accent="var(--color-accent)"
                  key={unit.list_unit_id}
                  label={unit.unit_name}
                  maxValue={maxSelectedEv}
                  meleeValue={result.melee_ev}
                  rangedValue={result.ranged_ev}
                  value={result.ev}
                  valueLabel={`${result.ev.toFixed(2)} total EV`}
                />
              )
            })}
          </div>
        </div>

        <div className="app-card">
          <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>Toughness</h3>
          <div className="mt-4 grid gap-3">
            {toughnessUnits.map((unit) => (
              <AnalysisBar
                accent="var(--color-warning)"
                key={unit.list_unit_id}
                label={unit.unit_name}
                maxValue={maxToughness}
                value={unit.effective_wounds}
                valueLabel={`${unit.effective_wounds.toFixed(2)} toughness`}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border shadow-sm" style={{ background: 'var(--color-surface-raised)', borderColor: 'var(--color-border)' }}>
        <table className="w-full min-w-[820px] border-collapse text-sm">
          <thead className="text-left" style={{ background: 'var(--color-bg-soft)', color: 'var(--color-text-muted)' }}>
            <tr>
              <SortableHeader
                active={sort.kind === 'unit'}
                direction={sort.direction}
                label="Unit"
                onClick={() => updateSort({ kind: 'unit', direction: 'asc' })}
              />
              <SortableHeader
                active={sort.kind === 'toughness'}
                direction={sort.direction}
                label="Toughness"
                onClick={() => updateSort({ kind: 'toughness', direction: 'desc' })}
              />
              <SortableHeader
                active={sort.kind === 'durability'}
                direction={sort.direction}
                label="Toughness / 100 pts"
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
                  {unit.effective_wounds.toFixed(2)}
                </td>
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
                        Ranged {result.ranged_ev.toFixed(2)} / Melee {result.melee_ev.toFixed(2)}
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

function AnalysisBar({
  accent,
  label,
  maxValue,
  meleeValue,
  rangedValue,
  value,
  valueLabel,
}: {
  accent: string
  label: string
  maxValue: number
  meleeValue?: number
  rangedValue?: number
  value: number
  valueLabel: string
}) {
  const width = maxValue > 0 ? Math.min(100, (value / maxValue) * 100) : 0
  const hasSplit = rangedValue !== undefined && meleeValue !== undefined
  const rangedWidth = maxValue > 0 && rangedValue !== undefined ? Math.min(100, (rangedValue / maxValue) * 100) : 0
  const meleeWidth = maxValue > 0 && meleeValue !== undefined ? Math.min(100, (meleeValue / maxValue) * 100) : 0

  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-semibold" style={{ color: 'var(--color-text)' }}>{label}</span>
        <span className="app-muted">{valueLabel}</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded" style={{ background: 'var(--color-bg-soft)' }}>
        {hasSplit ? (
          <div className="flex h-full">
            <div
              className="h-full"
              title={`Ranged ${rangedValue.toFixed(2)}`}
              style={{
                background: 'var(--color-accent)',
                width: `${rangedWidth}%`,
              }}
            />
            <div
              className="h-full"
              title={`Melee ${meleeValue.toFixed(2)}`}
              style={{
                background: 'var(--color-warning)',
                width: `${meleeWidth}%`,
              }}
            />
          </div>
        ) : (
          <div
            className="h-full"
            style={{
              background: accent,
              width: `${width}%`,
            }}
          />
        )}
      </div>
      {hasSplit ? (
        <div className="app-muted mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs">
          <span>Ranged {rangedValue.toFixed(2)}</span>
          <span>Melee {meleeValue.toFixed(2)}</span>
        </div>
      ) : null}
    </div>
  )
}

function ListHealthWeb({ metrics }: { metrics: ListHealthMetric[] }) {
  const center = 120
  const radius = 82
  const webPoints = metrics.map((metric, index) =>
    radarPoint(index, metrics.length, center, radius * (metric.score / 100)),
  )
  const polygonPoints = webPoints.map((point) => `${point.x},${point.y}`).join(' ')
  const averageScore = Math.round(metrics.reduce((sum, metric) => sum + metric.score, 0) / Math.max(1, metrics.length))

  return (
    <section className="app-card overflow-hidden">
      <div className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)] lg:items-center">
        <div className="relative mx-auto w-full max-w-[280px]">
          <svg
            aria-label="Balanced list web graph"
            className="h-auto w-full"
            role="img"
            viewBox="0 0 240 240"
          >
            {[0.25, 0.5, 0.75, 1].map((scale) => (
              <polygon
                fill="none"
                key={scale}
                points={metrics
                  .map((_, index) => radarPoint(index, metrics.length, center, radius * scale))
                  .map((point) => `${point.x},${point.y}`)
                  .join(' ')}
                stroke="var(--color-border)"
                strokeWidth="1"
              />
            ))}
            {metrics.map((_, index) => {
              const outerPoint = radarPoint(index, metrics.length, center, radius)
              return (
                <line
                  key={index}
                  stroke="var(--color-border)"
                  strokeWidth="1"
                  x1={center}
                  x2={outerPoint.x}
                  y1={center}
                  y2={outerPoint.y}
                />
              )
            })}
            {metrics.map((metric, index) => {
              const labelPoint = radarPoint(index, metrics.length, center, radius + 24)
              return (
                <text
                  dominantBaseline="middle"
                  fill="var(--color-text-muted)"
                  fontSize="10"
                  fontWeight="700"
                  key={`${metric.id}-label`}
                  textAnchor="middle"
                  x={labelPoint.x}
                  y={labelPoint.y}
                >
                  {graphAxisLabel(metric)}
                </text>
              )
            })}
            <polygon
              fill="var(--color-accent)"
              fillOpacity="0.22"
              points={polygonPoints}
              stroke="var(--color-accent)"
              strokeLinejoin="round"
              strokeWidth="3"
            />
            {webPoints.map((point, index) => (
              <circle
                cx={point.x}
                cy={point.y}
                fill="var(--color-surface-raised)"
                key={metrics[index].id}
                r="4"
                stroke="var(--color-accent)"
                strokeWidth="2"
              />
            ))}
            <circle cx={center} cy={center} fill="var(--color-surface-raised)" r="29" stroke="var(--color-border)" />
            <text
              dominantBaseline="middle"
              fill="var(--color-text)"
              fontSize="24"
              fontWeight="700"
              textAnchor="middle"
              x={center}
              y={center - 5}
            >
              {averageScore}
            </text>
            <text
              dominantBaseline="middle"
              fill="var(--color-text-subtle)"
              fontSize="10"
              fontWeight="700"
              textAnchor="middle"
              x={center}
              y={center + 16}
            >
              PROFILE
            </text>
          </svg>
        </div>
        <div>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
                Balanced list profile
              </h3>
              <p className="app-muted mt-1 text-sm">
                Balanced list profile derived from current analysis.
              </p>
            </div>
            <p className="rounded border px-3 py-2 text-sm font-semibold" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
              {averageScore} overall
            </p>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {metrics.map((metric) => (
              <div className="rounded border p-3" key={metric.id} style={{ borderColor: 'var(--color-border)' }}>
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold" style={{ color: 'var(--color-text)' }}>{metric.label}</p>
                  <span className="text-sm font-bold" style={{ color: statusColor(metric.status) }}>
                    {metric.score}
                  </span>
                </div>
                <p className="mt-1 text-xs font-semibold uppercase" style={{ color: statusColor(metric.status) }}>
                  {metric.status}
                </p>
                <p className="app-muted mt-2 text-sm">{metric.summary}</p>
              </div>
            ))}
          </div>
        </div>
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
    if (sort.kind === 'toughness') {
      const leftValue = left.effective_wounds
      const rightValue = right.effective_wounds
      if (leftValue === rightValue) {
        return left.unit_name.localeCompare(right.unit_name)
      }
      return direction * (leftValue - rightValue)
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
  if (
    left.kind === 'unit' ||
    left.kind === 'toughness' ||
    left.kind === 'durability' ||
    right.kind === 'unit' ||
    right.kind === 'toughness' ||
    right.kind === 'durability'
  ) {
    return true
  }
  return isTargetSort(left) && isTargetSort(right) && left.targetId === right.targetId
}

function isTargetSort(sort: AnalysisSort): sort is Extract<AnalysisSort, { targetId: string }> {
  return sort.kind === 'ev' || sort.kind === 'efficiency'
}

function buildListHealthMetrics(
  armyList: ArmyList,
  units: Unit[],
  analysis: ListAnalysisResult,
): ListHealthMetric[] {
  const unitLookup = new Map(units.map((unit) => [unit.id, unit]))
  const effectiveEntries = armyList.units.filter((entry) => entry.parent_entry === null)
  const activationTarget = armyList.point_limit >= 1500 ? 7 : 5
  const mobileEntries = effectiveEntries.filter((entry) => entryHasAnyRule(entry, unitLookup, MOBILITY_RULES))
  const castingTarget = armyList.point_limit >= 1500 ? 3 : 1
  const castingPower = totalCastingPower(armyList, unitLookup)
  const averageWoundsPer100 = average(analysis.totals.map((total) => total.wounds_per_100_points))
  const averageDurability = average(analysis.units.map((unit) => unit.effective_wounds_per_100_points))
  const weakestTarget = [...analysis.totals].sort((left, right) => left.wounds_per_100_points - right.wounds_per_100_points)[0]
  const weakestTargetName = analysis.targets.find((target) => target.id === weakestTarget?.target_id)?.name ?? 'No target'
  const totalRanged = analysis.totals.reduce((sum, total) => sum + total.ranged_ev, 0)
  const totalMelee = analysis.totals.reduce((sum, total) => sum + total.melee_ev, 0)
  const totalDamage = totalRanged + totalMelee
  const rangedShare = totalDamage > 0 ? totalRanged / totalDamage : 0
  const meleeShare = totalDamage > 0 ? totalMelee / totalDamage : 0
  const battlelineScore = totalDamage > 0 ? clampScore((Math.min(rangedShare, meleeShare) / 0.35) * 100) : 0

  return [
    metric(
      'activation-health',
      'Activation Health',
      clampScore((effectiveEntries.length / activationTarget) * 100),
      `${effectiveEntries.length} effective activations / target ${activationTarget}`,
    ),
    metric(
      'objective-reach',
      'Objective Reach',
      effectiveEntries.length > 0 ? clampScore((mobileEntries.length / effectiveEntries.length) * 100) : 0,
      `${mobileEntries.length} of ${effectiveEntries.length} effective units show reach rules`,
    ),
    metric(
      'casting-support',
      'Casting Support',
      clampScore((castingPower / castingTarget) * 100),
      `${castingPower} casting power / target ${castingTarget}`,
    ),
    metric(
      'damage-pressure',
      'Damage Pressure',
      clampScore((averageWoundsPer100 / 0.75) * 100),
      `${averageWoundsPer100.toFixed(2)} avg wounds / 100 pts`,
    ),
    metric(
      'durability',
      'Durability',
      clampScore((averageDurability / 12) * 100),
      `${averageDurability.toFixed(2)} avg effective wounds / 100 pts`,
    ),
    metric(
      'threat-coverage',
      'Threat Coverage',
      clampScore(((weakestTarget?.wounds_per_100_points ?? 0) / 0.6) * 100),
      `${weakestTargetName} is the lowest lane at ${(weakestTarget?.wounds_per_100_points ?? 0).toFixed(2)} wounds / 100 pts`,
    ),
    metric(
      'battleline-balance',
      'Battleline Balance',
      battlelineScore,
      `${Math.round(rangedShare * 100)}% ranged / ${Math.round(meleeShare * 100)}% melee`,
    ),
  ]
}

const MOBILITY_RULES = new Set(['aircraft', 'ambush', 'fast', 'flying', 'scout', 'strider', 'transport'])

function metric(id: string, label: string, score: number, summary: string): ListHealthMetric {
  return {
    id,
    label,
    score,
    status: metricStatus(score),
    summary,
  }
}

function graphAxisLabel(metric: ListHealthMetric) {
  const labels: Record<string, string> = {
    'activation-health': 'Activation',
    'objective-reach': 'Reach',
    'casting-support': 'Casting',
    'damage-pressure': 'Damage',
    durability: 'Durability',
    'threat-coverage': 'Coverage',
    'battleline-balance': 'Balance',
  }
  return labels[metric.id] ?? metric.label
}

function metricStatus(score: number): ListHealthMetric['status'] {
  if (score >= 75) {
    return 'Strong'
  }
  if (score >= 45) {
    return 'Watch'
  }
  return 'Gap'
}

function statusColor(status: ListHealthMetric['status']) {
  if (status === 'Strong') {
    return 'var(--color-success)'
  }
  if (status === 'Watch') {
    return 'var(--color-warning)'
  }
  return 'var(--color-danger)'
}

function entryHasAnyRule(entry: ListUnit, unitLookup: Map<number, Unit>, rules: Set<string>) {
  const unit = unitLookup.get(entry.unit)
  if (!unit) {
    return false
  }
  return rulesForEntry(entry, unit).some((rule) => rules.has(rule))
}

function totalCastingPower(armyList: ArmyList, unitLookup: Map<number, Unit>) {
  return armyList.units.reduce((sum, entry) => sum + castingPowerForEntry(entry, unitLookup), 0)
}

function castingPowerForEntry(entry: ListUnit, unitLookup: Map<number, Unit>) {
  const unit = unitLookup.get(entry.unit)
  if (!unit) {
    return 0
  }
  const rules = specialRulesForEntry(entry, unit)
  const casterPower = castingRuleValue(rules.get('caster'))
  const casterGroupPower = rules.has('caster group') && rules.get('caster group') !== false ? 1 : 0
  return Math.max(casterPower, casterGroupPower)
}

function rulesForEntry(entry: ListUnit, unit: Unit) {
  return [...specialRulesForEntry(entry, unit).keys()]
}

function specialRulesForEntry(entry: ListUnit, unit: Unit) {
  const rules = new Map<string, unknown>()
  for (const [rule, value] of Object.entries(unit.special_rules)) {
    addSpecialRule(rules, rule, value)
  }
  for (const section of unit.upgrade_sections) {
    for (const option of section.options) {
      if (!entry.selected_upgrades.includes(option.id)) {
        continue
      }
      for (const gainedRule of option.gains) {
        addGainRules(rules, gainedRule)
      }
    }
  }
  return rules
}

function addGainRules(rules: Map<string, unknown>, gain: Record<string, unknown>) {
  const content = gain.content
  if (Array.isArray(content)) {
    for (const contentRule of content) {
      if (!isRuleRecord(contentRule)) {
        continue
      }
      const name = contentRule.name
      if (typeof name === 'string') {
        addSpecialRule(rules, name, contentRule.rating ?? true)
      }
    }
    return
  }

  const name = gain.name
  if (typeof name === 'string') {
    addSpecialRule(rules, name, gain.rating ?? true)
    return
  }

  for (const [rule, value] of Object.entries(gain)) {
    addSpecialRule(rules, rule, value)
  }
}

function isRuleRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function addSpecialRule(rules: Map<string, unknown>, rule: string, value: unknown) {
  const normalized = normalizeRule(rule)
  if (!normalized) {
    return
  }
  if (normalized === 'caster' && rules.has(normalized)) {
    rules.set(normalized, Math.max(castingRuleValue(rules.get(normalized)), castingRuleValue(value)))
    return
  }
  rules.set(normalized, value)
}

function castingRuleValue(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.max(0, value)
  }
  if (typeof value === 'string') {
    const parsed = Number(value.trim())
    return Number.isFinite(parsed) ? Math.max(0, parsed) : 0
  }
  return value === true ? 1 : 0
}

function normalizeRule(rule: string) {
  return rule.trim().toLowerCase()
}

function average(values: number[]) {
  if (values.length === 0) {
    return 0
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function clampScore(value: number) {
  if (!Number.isFinite(value)) {
    return 0
  }
  return Math.max(0, Math.min(100, Math.round(value)))
}

function radarPoint(index: number, total: number, center: number, radius: number) {
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / total
  return {
    x: roundSvgPoint(center + Math.cos(angle) * radius),
    y: roundSvgPoint(center + Math.sin(angle) * radius),
  }
}

function roundSvgPoint(value: number) {
  return Math.round(value * 100) / 100
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
      ranged_ev: 0,
      melee_ev: 0,
      wounds_per_100_points: 0,
      ranged_wounds_per_100_points: 0,
      melee_wounds_per_100_points: 0,
      p_kill_model: 0,
    }
  )
}
