import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../api/client'
import type { AdvisorSuggestionResponse, Faction } from '../api/types'

const LIST_STYLE_PROMPTS = [
  {
    title: 'Mobile objective pressure',
    description: 'Higher activation count, fast scoring units, and enough threat to clear contested markers.',
    prompt:
      'Build a mobile objective pressure list with enough activations to trade onto objectives, fast scoring pieces, and just enough damage to remove common contesting units.',
  },
  {
    title: 'Elite hammer',
    description: 'Fewer durable threats, embedded support, and concentrated AP for forcing decisive fights.',
    prompt:
      'Build an elite hammer list with durable primary threats, embedded hero support where it matters, and high-AP damage for breaking tough enemy units.',
  },
  {
    title: 'Balanced combined arms',
    description: 'A stable mix of scoring bodies, ranged pressure, melee threat, anti-tough tools, and support.',
    prompt:
      'Build a balanced combined-arms list with scoring bodies, ranged pressure, melee counterpunch, anti-tough tools, and support pieces that cover common matchups.',
  },
  {
    title: 'Beginner forgiving',
    description: 'Simple roles, resilient units, fewer fragile tricks, and a clear plan for the first three rounds.',
    prompt:
      'Build a beginner-friendly list with straightforward unit roles, resilient choices, limited fragile combos, and a clear plan for playing the first three rounds.',
  },
] as const

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
        <p className="app-muted mt-2 text-sm leading-6">
          Choose a faction, then describe the job you want the army to do. The advisor can draft objective lists,
          elite hammers, balanced forces, or beginner-friendly armies.
        </p>

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
          List goal
          <textarea
            className="app-field mt-1 min-h-36 w-full"
            maxLength={2000}
            onChange={(event) => {
              setPrompt(event.target.value)
              setResult(null)
            }}
            placeholder="Example: Build a mobile objective list with enough activations to contest late and enough AP to remove tough units."
            value={prompt}
          />
        </label>

        <section className="mt-5" aria-labelledby="advisor-list-styles">
          <h2 className="text-sm font-semibold" id="advisor-list-styles" style={{ color: 'var(--color-text)' }}>
            List styles you can ask for
          </h2>
          <div className="mt-3 grid gap-3">
            {LIST_STYLE_PROMPTS.map((style) => (
              <button
                className="rounded border p-3 text-left transition hover:-translate-y-0.5"
                disabled={submitting !== null}
                key={style.title}
                onClick={() => {
                  setPrompt(style.prompt)
                  setResult(null)
                }}
                style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-soft)' }}
                type="button"
              >
                <span className="block text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                  {style.title}
                </span>
                <span className="app-muted mt-1 block text-xs leading-5">{style.description}</span>
                <span className="sr-only">Use {style.title} prompt</span>
              </button>
            ))}
          </div>
        </section>

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
        <p className="app-muted mt-2 text-sm leading-6">
          Preview a draft before creating it. The result will show the generated archetype, playstyle, unit roles,
          warnings, activation shape, and how closely the suggestion fits the point limit.
        </p>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {LIST_STYLE_PROMPTS.map((style) => (
            <div className="rounded border px-3 py-2" key={style.title} style={{ borderColor: 'var(--color-border)' }}>
              <p className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{style.title}</p>
              <p className="app-muted mt-1 text-xs leading-5">{style.description}</p>
            </div>
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
                  {unit.combined_from_count > 1 ? `, combined x${unit.combined_from_count}` : ''}
                </p>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
