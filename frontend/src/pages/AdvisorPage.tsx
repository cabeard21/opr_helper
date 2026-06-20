import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { AdvisorSuggestionResponse, Faction } from '../api/types'

export function AdvisorPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [factions, setFactions] = useState<Faction[]>([])
  const [factionId, setFactionId] = useState<number | ''>('')
  const [pointLimit, setPointLimit] = useState(2000)
  const [prompt, setPrompt] = useState('')
  const [result, setResult] = useState<AdvisorSuggestionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState<'preview' | 'create' | null>(null)

  useEffect(() => {
    apiClient
      .getFactions()
      .then((nextFactions) => {
        setFactions(nextFactions)
        const requestedFaction = Number(searchParams.get('faction'))
        const initialFaction = nextFactions.find((faction) => faction.id === requestedFaction) ?? nextFactions[0]
        setFactionId(initialFaction?.id ?? '')
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [searchParams])

  const selectedFaction = useMemo(
    () => factions.find((faction) => faction.id === factionId),
    [factionId, factions],
  )

  async function requestSuggestion(dryRun: boolean) {
    if (!factionId) {
      setError('Choose a faction before requesting a suggestion.')
      return
    }
    if (!prompt.trim()) {
      setError('Describe what you want the list to do.')
      return
    }
    if (pointLimit <= 0) {
      setError('Point limit must be positive.')
      return
    }

    setSubmitting(dryRun ? 'preview' : 'create')
    setError(null)
    try {
      const nextResult = await apiClient.suggestArmyList({
        faction: factionId,
        point_limit: pointLimit,
        prompt: prompt.trim(),
        dry_run: dryRun,
        ...(dryRun || !result ? {} : { suggestion: result.suggestion }),
      })
      setResult(nextResult)
      if (!dryRun && nextResult.army_list) {
        navigate(`/lists/${nextResult.army_list.id}`)
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(null)
    }
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
      <form className="app-card-lg">
        <Link className="app-link" to="/lists">
          Back to lists
        </Link>
        <h1 className="app-heading mt-2">Army advisor</h1>

        {error ? <p className="app-alert-danger mt-4 text-sm">{error}</p> : null}
        {loading ? <p className="app-muted mt-4 text-sm">Loading factions...</p> : null}

        <label className="app-label mt-5 block">
          Faction
          <select
            className="app-field mt-1 w-full"
            disabled={loading || submitting !== null}
            onChange={(event) => {
              setFactionId(Number(event.target.value))
              setResult(null)
            }}
            value={factionId}
          >
            {factions.map((faction) => (
              <option key={faction.id} value={faction.id}>
                {faction.name}
              </option>
            ))}
          </select>
        </label>

        <label className="app-label mt-4 block">
          Point limit
          <input
            className="app-field mt-1 w-full"
            min={1}
            onChange={(event) => {
              setPointLimit(Number(event.target.value))
              setResult(null)
            }}
            type="number"
            value={pointLimit}
          />
        </label>

        <label className="app-label mt-4 block">
          Goal
          <textarea
            className="app-field mt-1 min-h-36 w-full"
            maxLength={2000}
            onChange={(event) => {
              setPrompt(event.target.value)
              setResult(null)
            }}
            value={prompt}
          />
        </label>

        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          <button
            className="app-button-secondary"
            disabled={submitting !== null}
            onClick={() => requestSuggestion(true)}
            type="button"
          >
            {submitting === 'preview' ? 'Previewing...' : 'Preview suggestion'}
          </button>
          <button
            className="app-button-primary"
            disabled={submitting !== null}
            onClick={() => requestSuggestion(false)}
            type="button"
          >
            {submitting === 'create' ? 'Creating...' : 'Create list'}
          </button>
        </div>
      </form>

      <AdvisorPreview pointLimit={pointLimit} result={result} selectedFaction={selectedFaction} />
    </section>
  )
}

function AdvisorPreview({
  pointLimit,
  result,
  selectedFaction,
}: {
  pointLimit: number
  result: AdvisorSuggestionResponse | null
  selectedFaction?: Faction
}) {
  if (!result) {
    return (
      <section className="app-card-lg">
        <h2 className="app-subheading">{selectedFaction?.name ?? 'Suggestion preview'}</h2>
        <p className="app-muted mt-2 text-sm">No suggestion loaded yet.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {['Aggressive elite list', 'High activation objective play', 'Anti-tough damage', 'Beginner friendly'].map((example) => (
            <span className="rounded border px-2 py-1 text-xs font-semibold" key={example} style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
              {example}
            </span>
          ))}
        </div>
      </section>
    )
  }

  const warnings = [...result.suggestion.warnings, ...result.reconciliation_warnings]

  return (
    <section className="grid gap-4">
      <div className="app-card-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="app-section-heading">{result.suggestion.archetype}</h2>
            <p className="mt-1 text-sm font-semibold" style={{ color: 'var(--color-accent)' }}>{result.suggestion.playstyle}</p>
          </div>
          <div className="text-right">
            <p className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>
              {result.computed_total_points.toLocaleString()} / {pointLimit.toLocaleString()} pts
            </p>
            <p className="app-muted text-sm">
              {result.point_delta >= 0
                ? `${result.point_delta.toLocaleString()} pts remaining`
                : `${Math.abs(result.point_delta).toLocaleString()} pts over`}
            </p>
          </div>
        </div>
        <p className="app-muted mt-4 text-sm leading-6">{result.suggestion.strategy_summary}</p>
      </div>

      {warnings.length > 0 ? (
        <div className="app-alert-warning text-sm">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}

      <div className="grid gap-3">
        {result.suggestion.units.length === 0 ? (
          <p className="app-card app-muted text-sm">No valid units suggested.</p>
        ) : null}
        {result.suggestion.units.map((unit, index, units) => {
          const host = unit.parent_unit_index == null ? null : units[unit.parent_unit_index]
          return (
            <article className="app-card" key={`${unit.unit_id}-${index}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>{unit.unit_name}</h3>
                  {host ? <p className="mt-1 text-sm font-semibold" style={{ color: 'var(--color-accent)' }}>Embedded in {host.unit_name}</p> : null}
                  <p className="app-muted mt-1 text-sm">{unit.justification}</p>
                </div>
                <p className="rounded border px-2 py-1 text-sm font-semibold" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
                  x{unit.model_count}
                </p>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
