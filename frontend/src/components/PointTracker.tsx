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
      className={`rounded-md border bg-white p-4 shadow-sm ${
        overBy > 0 ? 'border-red-300' : 'border-stone-200'
      }`}
      aria-label="Point tracker"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-stone-500">Army points</p>
          <p className="text-2xl font-semibold text-stone-950">
            {totalPoints.toLocaleString()} / {pointLimit.toLocaleString()} pts
          </p>
        </div>
        <div
          className={`rounded px-3 py-1 text-sm font-semibold ${
            overBy > 0 ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
          }`}
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
        className="mt-4 h-2 overflow-hidden rounded bg-stone-200"
      >
        <div
          className={`h-full ${overBy > 0 ? 'bg-red-500' : 'bg-emerald-600'}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className={`mt-3 text-sm font-medium ${overBy > 0 ? 'text-red-700' : 'text-stone-600'}`}>
        {overBy > 0 ? `${overBy.toLocaleString()} pts over` : `${remaining.toLocaleString()} pts remaining`}
      </p>
    </section>
  )
}
