type PointTrackerProps = {
  pointLimit: number
  totalPoints: number
}

export function PointTracker({ pointLimit, totalPoints }: PointTrackerProps) {
  const overBy = Math.max(0, totalPoints - pointLimit)
  const remaining = Math.max(0, pointLimit - totalPoints)
  const percentage = pointLimit > 0 ? Math.min(100, Math.round((totalPoints / pointLimit) * 100)) : 0
  const status = overBy > 0 ? 'Over limit' : 'Legal'

  return (
    <section
      className="app-card"
      style={{ borderColor: overBy > 0 ? 'var(--color-danger)' : 'var(--color-border)' }}
      aria-label="Point tracker"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="app-subtle text-sm font-medium">Army points</p>
          <p className="text-2xl font-semibold" style={{ color: 'var(--color-text)' }}>
            {totalPoints.toLocaleString()} / {pointLimit.toLocaleString()} pts
          </p>
        </div>
        <div
          className="rounded px-3 py-1 text-sm font-semibold"
          style={{
            background: overBy > 0 ? 'var(--color-danger-soft)' : 'var(--color-success-soft)',
            color: overBy > 0 ? 'var(--color-danger)' : 'var(--color-success)',
          }}
        >
          {status}
        </div>
      </div>
      <div
        role="meter"
        aria-label="Point limit usage"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percentage}
        className="mt-4 h-2 overflow-hidden rounded"
        style={{ background: 'var(--color-bg-soft)' }}
      >
        <div
          className="h-full"
          style={{
            background: overBy > 0 ? 'var(--color-danger)' : 'var(--color-success)',
            width: `${percentage}%`,
          }}
        />
      </div>
      <p className="mt-3 text-sm font-medium" style={{ color: overBy > 0 ? 'var(--color-danger)' : 'var(--color-text-muted)' }}>
        {overBy > 0 ? `${overBy.toLocaleString()} pts over` : `${remaining.toLocaleString()} pts remaining`}
      </p>
    </section>
  )
}
