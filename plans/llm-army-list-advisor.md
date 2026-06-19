# LLM Army List Advisor

## Objective

Add an AI-powered advisor that accepts a faction, point limit, and natural-language goal, then returns an OPR Age of Fantasy army list suggestion grounded in local unit data, computed combat metrics, and list-building doctrine.

The advisor is provider-neutral at the application boundary. The current implemented provider is OpenAI with `OPENAI_MODEL=gpt-5.5` by default. ChatGPT subscription state is not used by this feature; API access is configured through environment variables.

## Current Implementation

Backend:

- `GET /api/advisor/` returns advisor readiness plus configured provider/model.
- `POST /api/advisor/suggest/` accepts `faction`, `point_limit`, `prompt`, and optional `dry_run`.
- `advisor.unit_scorer` computes per-unit offense, resilience, mobility, morale, and ranged flags from local faction data.
- `advisor.context_builder` compacts scored unit data and OPR doctrine into an LLM context.
- `advisor.llm_service` uses an `AdvisorProvider` protocol and an OpenAI Responses API implementation with structured Pydantic output.
- `advisor.reconciliation` validates LLM output against database truth before returning or creating a list.
- `advisor.rate_limit` applies a fixed-window local rate limit to expensive advisor calls.

Frontend:

- `/advisor` provides a faction/point-limit/goal form.
- Preview mode returns the suggestion without writing to the database.
- Create mode persists the reconciled suggestion as an `ArmyList`.
- The preview shows archetype, playstyle, strategy, unit justifications, computed point totals, point delta, and warnings.

## Public API Contract

Request:

```json
{
  "faction": 1,
  "point_limit": 2000,
  "prompt": "Aggressive elite list with mobility and anti-tough damage.",
  "dry_run": true
}
```

Response envelope:

```json
{
  "data": {
    "suggestion": {
      "units": [
        {
          "unit_id": 10,
          "unit_name": "Paladins",
          "model_count": 1,
          "justification": "Durable high-AP center pressure."
        }
      ],
      "total_points": 180,
      "archetype": "Offensive Elite",
      "playstyle": "Shove It In",
      "activation_count": 1,
      "strategy_summary": "Push the center and score with support pieces.",
      "warnings": []
    },
    "computed_total_points": 180,
    "point_delta": 1820,
    "reconciliation_warnings": [],
    "army_list": null
  },
  "error": null
}
```

Status behavior:

- `200`: dry-run suggestion returned.
- `201`: list created from a reconciled suggestion.
- `400`: malformed request.
- `404`: unknown faction.
- `422`: create-list request had no valid suggested units after reconciliation.
- `429`: advisor rate limit exceeded.
- `502`: provider failure or invalid structured provider output.

## Safety Invariants

- Never hardcode API keys. Use `OPENAI_API_KEY` and `.env`/deployment secrets.
- Never trust LLM-provided point totals. Recompute points from local models and selected/default slots.
- Never create wrong-faction, unknown, or out-of-bounds unit entries.
- Preserve LLM and reconciliation warnings in the response.
- Keep provider internals out of user-facing error messages.
- Do not make real provider calls in automated tests.

## Next Phases

1. Add optional provider implementations behind the existing `AdvisorProvider` protocol only when needed.
2. Add persisted advisor telemetry if the app needs auditability: provider, model, prompt hash, latency, reconciliation warnings, and created list id.
3. Add richer list-building constraints: max single-unit point share, required activation band, role coverage, and optional tournament profile presets.
4. Add E2E coverage for the `/advisor` preview and create-list browser flow once Playwright is introduced for this repo.
5. Add prompt/version snapshots if advisor quality tuning becomes frequent.

## Verification

Backend:

```powershell
.\.venv\Scripts\python -m pytest backend -q
.\.venv\Scripts\python backend\manage.py check
```

Frontend:

```powershell
cmd /c npm run test --prefix frontend
cmd /c npm run build --prefix frontend
```
