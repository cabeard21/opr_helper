import type { Unit } from '../api/types'

type UnitCardProps = {
  unit: Unit
  onAdd?: (unit: Unit) => void
}

function formatRules(rules: Record<string, unknown>) {
  const entries = Object.entries(rules)
  if (entries.length === 0) {
    return 'No special rules'
  }
  return entries
    .map(([name, value]) => (value === true ? name : `${name} ${String(value)}`))
    .join(', ')
}

export function UnitCard({ unit, onAdd }: UnitCardProps) {
  const defaultWeapon = unit.weapon_slots.find((slot) => slot.is_default) ?? unit.weapon_slots[0]

  return (
    <article className="rounded-md border border-stone-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-stone-950">{unit.name}</h3>
          <p className="mt-1 text-sm text-stone-600">{unit.points.toLocaleString()} pts</p>
        </div>
        {onAdd ? (
          <button
            className="rounded bg-stone-950 px-3 py-2 text-sm font-semibold text-white hover:bg-stone-800"
            onClick={() => onAdd(unit)}
            type="button"
          >
            Add {unit.name}
          </button>
        ) : null}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
        <div className="rounded bg-teal-50 px-2 py-2 text-teal-900">
          <span className="block text-xs font-medium text-teal-700">QU</span>
          <span className="font-semibold">{unit.quality}+</span>
        </div>
        <div className="rounded bg-indigo-50 px-2 py-2 text-indigo-900">
          <span className="block text-xs font-medium text-indigo-700">DE</span>
          <span className="font-semibold">{unit.defense}+</span>
        </div>
        <div className="rounded bg-amber-50 px-2 py-2 text-amber-900">
          <span className="block text-xs font-medium text-amber-700">T</span>
          <span className="font-semibold">{unit.tough}</span>
        </div>
      </div>
      <p className="mt-4 text-sm text-stone-700">{formatRules(unit.special_rules)}</p>
      {defaultWeapon ? (
        <p className="mt-3 rounded bg-stone-100 px-3 py-2 text-sm text-stone-700">
          {defaultWeapon.weapon.name} · {defaultWeapon.weapon.attacks_string} · AP{defaultWeapon.weapon.ap}
        </p>
      ) : null}
    </article>
  )
}
