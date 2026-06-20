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
  const defaultWeapons = unit.weapon_slots.filter((slot) => slot.is_default)
  const displayWeapons = defaultWeapons.length > 0 ? defaultWeapons : unit.weapon_slots.slice(0, 1)

  return (
    <article className="app-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>{unit.name}</h3>
          <p className="app-muted mt-1 text-sm">{unit.points.toLocaleString()} pts</p>
        </div>
        {onAdd ? (
          <button
            className="app-button-primary"
            onClick={() => onAdd(unit)}
            type="button"
          >
            Add {unit.name}
          </button>
        ) : null}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
        <div className="rounded px-2 py-2" style={{ background: 'var(--color-accent-soft)', color: 'var(--color-text)' }}>
          <span className="block text-xs font-medium" style={{ color: 'var(--color-accent)' }}>QU</span>
          <span className="font-semibold">{unit.quality}+</span>
        </div>
        <div className="rounded px-2 py-2" style={{ background: 'var(--color-bg-soft)', color: 'var(--color-text)' }}>
          <span className="app-subtle block text-xs font-medium">DE</span>
          <span className="font-semibold">{unit.defense}+</span>
        </div>
        <div className="rounded px-2 py-2" style={{ background: 'var(--color-warning-soft)', color: 'var(--color-warning)' }}>
          <span className="block text-xs font-medium">T</span>
          <span className="font-semibold">{unit.tough}</span>
        </div>
      </div>
      <p className="app-muted mt-4 text-sm">{formatRules(unit.special_rules)}</p>
      {displayWeapons.length > 0 ? (
        <p className="app-muted mt-3 rounded px-3 py-2 text-sm" style={{ background: 'var(--color-bg-soft)' }}>
          {displayWeapons
            .map((slot) => `${slot.weapon.name} - ${slot.weapon.attacks_string} - AP${slot.weapon.ap}`)
            .join(' + ')}
        </p>
      ) : null}
    </article>
  )
}
