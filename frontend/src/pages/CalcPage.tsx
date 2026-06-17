import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { apiClient } from '../api/client'
import type { CalcResult, Faction, Unit } from '../api/types'

type TargetPreset = {
  id: string
  name: string
  defense: number
  tough: number
}

const TARGET_PRESETS: TargetPreset[] = [
  { id: 'light', name: 'Light Infantry', defense: 5, tough: 1 },
  { id: 'heavy', name: 'Heavy Infantry', defense: 3, tough: 3 },
  { id: 'monster', name: 'Monster', defense: 2, tough: 10 },
  { id: 'custom', name: 'Custom', defense: 4, tough: 1 },
]

function parsePositiveInt(value: string | null): number | null {
  if (!value) {
    return null
  }
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

export function CalcPage() {
  const [searchParams] = useSearchParams()
  const requestedFactionId = parsePositiveInt(searchParams.get('factionId'))
  const requestedUnitId = parsePositiveInt(searchParams.get('unitId'))
  const requestedWeaponId = parsePositiveInt(searchParams.get('weaponId'))

  const [factions, setFactions] = useState<Faction[]>([])
  const [units, setUnits] = useState<Unit[]>([])
  const [selectedFactionId, setSelectedFactionId] = useState<number | null>(requestedFactionId)
  const [selectedUnitId, setSelectedUnitId] = useState<number | null>(requestedUnitId)
  const [selectedWeaponId, setSelectedWeaponId] = useState<number | null>(requestedWeaponId)
  const [targetPresetId, setTargetPresetId] = useState('light')
  const [customDefense, setCustomDefense] = useState(4)
  const [customTough, setCustomTough] = useState(1)
  const [stealth, setStealth] = useState(false)
  const [indirect, setIndirect] = useState(false)
  const [result, setResult] = useState<CalcResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadingFactions, setLoadingFactions] = useState(true)
  const [calculating, setCalculating] = useState(false)

  useEffect(() => {
    apiClient
      .getFactions()
      .then((nextFactions) => {
        setFactions(nextFactions)
        if (!requestedFactionId && nextFactions.length > 0) {
          setSelectedFactionId(nextFactions[0].id)
        }
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingFactions(false))
  }, [requestedFactionId])

  useEffect(() => {
    if (!selectedFactionId) {
      return
    }

    apiClient
      .getFactionUnits(selectedFactionId)
      .then((nextUnits) => {
        setUnits(nextUnits)
        const nextUnit = nextUnits.find((unit) => unit.id === requestedUnitId) ?? nextUnits[0]
        setSelectedUnitId(nextUnit?.id ?? null)
        const nextWeapon =
          nextUnit?.weapon_slots.find((slot) => slot.weapon.id === requestedWeaponId)?.weapon ??
          nextUnit?.weapon_slots.find((slot) => slot.is_default)?.weapon ??
          nextUnit?.weapon_slots[0]?.weapon
        setSelectedWeaponId(nextWeapon?.id ?? null)
      })
      .catch((err: Error) => setError(err.message))
  }, [selectedFactionId, requestedUnitId, requestedWeaponId])

  const selectedUnit = useMemo(
    () => units.find((unit) => unit.id === selectedUnitId) ?? null,
    [selectedUnitId, units],
  )
  const selectedWeapon = useMemo(
    () => selectedUnit?.weapon_slots.find((slot) => slot.weapon.id === selectedWeaponId)?.weapon ?? null,
    [selectedUnit, selectedWeaponId],
  )
  const targetPreset = TARGET_PRESETS.find((preset) => preset.id === targetPresetId) ?? TARGET_PRESETS[0]
  const target =
    targetPreset.id === 'custom'
      ? { defense: customDefense, tough: customTough }
      : { defense: targetPreset.defense, tough: targetPreset.tough }

  async function calculate() {
    if (!selectedUnit || !selectedWeapon) {
      setError('Select a unit and weapon before calculating.')
      return
    }

    setCalculating(true)
    setError(null)
    try {
      setResult(
        await apiClient.calculateEv({
          unit_id: selectedUnit.id,
          weapon_id: selectedWeapon.id,
          target,
          modifiers: { stealth, indirect },
        }),
      )
    } catch (err) {
      setResult(null)
      setError((err as Error).message)
    } finally {
      setCalculating(false)
    }
  }

  const chartData =
    result?.distribution.map((point) => ({
      wounds: point.wounds,
      probability: Number((point.probability * 100).toFixed(2)),
    })) ?? []

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link className="text-sm font-semibold text-teal-700" to="/lists">
            Back to lists
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-stone-950">Probability calculator</h1>
        </div>
      </div>

      {error ? <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</p> : null}

      <div className="grid gap-6 xl:grid-cols-[320px_320px_minmax(0,1fr)]">
        <section aria-label="Attacker" className="rounded-md border border-stone-200 bg-white p-4 shadow-sm">
          <h2 className="text-xl font-semibold text-stone-950">Attacker</h2>
          <div className="mt-4 grid gap-4">
            <label className="grid gap-1 text-sm font-semibold text-stone-700">
              Faction
              <select
                className="rounded border border-stone-300 px-3 py-2 font-normal text-stone-950"
                disabled={loadingFactions}
                onChange={(event) => {
                  setResult(null)
                  setSelectedFactionId(Number(event.target.value))
                  setSelectedUnitId(null)
                  setSelectedWeaponId(null)
                }}
                value={selectedFactionId ?? ''}
              >
                <option value="">Select faction</option>
                {factions.map((faction) => (
                  <option key={faction.id} value={faction.id}>
                    {faction.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1 text-sm font-semibold text-stone-700">
              Unit
              <select
                className="rounded border border-stone-300 px-3 py-2 font-normal text-stone-950"
                disabled={units.length === 0}
                onChange={(event) => {
                  const unitId = Number(event.target.value)
                  const unit = units.find((candidate) => candidate.id === unitId)
                  const weapon = unit?.weapon_slots.find((slot) => slot.is_default)?.weapon ?? unit?.weapon_slots[0]?.weapon
                  setResult(null)
                  setSelectedUnitId(unitId)
                  setSelectedWeaponId(weapon?.id ?? null)
                }}
                value={selectedUnitId ?? ''}
              >
                <option value="">Select unit</option>
                {units.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1 text-sm font-semibold text-stone-700">
              Weapon
              <select
                className="rounded border border-stone-300 px-3 py-2 font-normal text-stone-950"
                disabled={!selectedUnit || selectedUnit.weapon_slots.length === 0}
                onChange={(event) => {
                  setResult(null)
                  setSelectedWeaponId(Number(event.target.value))
                }}
                value={selectedWeaponId ?? ''}
              >
                <option value="">Select weapon</option>
                {selectedUnit?.weapon_slots.map((slot) => (
                  <option key={slot.weapon.id} value={slot.weapon.id}>
                    {slot.weapon.name} ({slot.weapon.attacks_string}, AP{slot.weapon.ap})
                  </option>
                ))}
              </select>
            </label>
          </div>
        </section>

        <section aria-label="Target" className="rounded-md border border-stone-200 bg-white p-4 shadow-sm">
          <h2 className="text-xl font-semibold text-stone-950">Target</h2>
          <div className="mt-4 grid gap-4">
            <label className="grid gap-1 text-sm font-semibold text-stone-700">
              Profile
              <select
                className="rounded border border-stone-300 px-3 py-2 font-normal text-stone-950"
                onChange={(event) => {
                  setResult(null)
                  setTargetPresetId(event.target.value)
                }}
                value={targetPresetId}
              >
                {TARGET_PRESETS.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.name} (DE{preset.defense}+ T{preset.tough})
                  </option>
                ))}
              </select>
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="grid gap-1 text-sm font-semibold text-stone-700">
                Defense
                <input
                  className="rounded border border-stone-300 px-3 py-2 font-normal text-stone-950"
                  disabled={targetPresetId !== 'custom'}
                  max={6}
                  min={2}
                  onChange={(event) => {
                    setResult(null)
                    setCustomDefense(Number(event.target.value))
                  }}
                  type="number"
                  value={target.defense}
                />
              </label>
              <label className="grid gap-1 text-sm font-semibold text-stone-700">
                Tough
                <input
                  className="rounded border border-stone-300 px-3 py-2 font-normal text-stone-950"
                  disabled={targetPresetId !== 'custom'}
                  min={1}
                  onChange={(event) => {
                    setResult(null)
                    setCustomTough(Number(event.target.value))
                  }}
                  type="number"
                  value={target.tough}
                />
              </label>
            </div>

            <label className="flex items-center gap-2 text-sm font-semibold text-stone-700">
              <input checked={stealth} onChange={(event) => setStealth(event.target.checked)} type="checkbox" />
              Stealth
            </label>
            <label className="flex items-center gap-2 text-sm font-semibold text-stone-700">
              <input checked={indirect} onChange={(event) => setIndirect(event.target.checked)} type="checkbox" />
              Indirect
            </label>

            <button
              className="rounded bg-stone-950 px-3 py-2 text-sm font-semibold text-white hover:bg-stone-800 disabled:opacity-50"
              disabled={calculating || !selectedUnit || !selectedWeapon}
              onClick={calculate}
              type="button"
            >
              {calculating ? 'Calculating...' : 'Calculate'}
            </button>
          </div>
        </section>

        <section aria-label="Results" className="rounded-md border border-stone-200 bg-white p-4 shadow-sm">
          <h2 className="text-xl font-semibold text-stone-950">Results</h2>
          {result ? (
            <div className="mt-4">
              <div className="grid gap-3 sm:grid-cols-4">
                <ResultStat label="Expected wounds" value={result.ev.toFixed(2)} />
                <ResultStat label="Zero wounds" value={formatPercent(result.p_zero_wounds)} />
                <ResultStat label="Kill model" value={formatPercent(result.p_kill_model)} />
                <ResultStat label="Kill unit" value={formatPercent(result.p_kill_unit)} />
              </div>
              <div aria-label="Wound probability histogram" className="mt-6 h-72 w-full" role="img">
                <ResponsiveContainer height="100%" width="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="wounds" />
                    <YAxis unit="%" />
                    <Tooltip />
                    <ReferenceLine stroke="#0f766e" x={Number(result.ev.toFixed(2))} />
                    <Bar dataKey="probability" fill="#0f766e" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-stone-600">Select an attacker and target, then calculate.</p>
          )}
        </section>
      </div>
    </section>
  )
}

type ResultStatProps = {
  label: string
  value: string
}

function ResultStat({ label, value }: ResultStatProps) {
  return (
    <div className="rounded border border-stone-200 bg-stone-50 p-3">
      <p className="text-xs font-semibold uppercase text-stone-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-stone-950">{value}</p>
    </div>
  )
}
