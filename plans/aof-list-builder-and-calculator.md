# OPR Age of Fantasy — List Builder & Probability Calculator

**Objective**: A web app that lets players build legal AoF army lists and see expected
wounds / probability distributions for their units against configurable targets.

**Reference**: `refs/40k_Army_builder/` — existing Django/DRF calculation engine that
established the callable-pipeline modifier pattern and dice-string EV helpers.
OPR data APIs: `https://opr.harve.dev/` and `https://army-forge.onepagerules.com/`.

---

## AoF Rules Quick-Reference (for implementers)

**Unit stats**: Quality (QU) · Defense (DE) · Tough (T) · points · special rules

**Weapon stats**: Range (inches, 0 = melee) · Attacks (A) · AP · special rules

**Attack sequence**:
1. Roll A dice → each rolls ≥ QU = hit
2. Per hit, defender rolls → defends on (DE − AP)+ (clamped to 2+–6+)
3. Failed defenses = wounds; wounds ≥ Tough removes model/unit

**Key specials that alter math**:

| Rule | Effect on calculation |
|---|---|
| Poison | Natural 6 to hit auto-wounds (skips defense) |
| Rending | Natural 6 to hit gives AP6 for that attack |
| Deadly(X) | Each wound counts as X wounds |
| Blast(X) | Auto-hits X times (no to-hit roll) |
| Furious | Natural 6 to hit generates +1 attack die |
| Stealth | Attackers suffer −1 to hit |
| Indirect | −1 to hit, ignores LoS |
| Regeneration(X) | Before morale, each wound rolls die → X+ = recovered |

---

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Backend | Python 3.12 + Django 5 + DRF | Mirrors ref project; team already knows it |
| DB | SQLite (dev) / PostgreSQL (prod) | Simple, migratable |
| Frontend | React 18 + TypeScript + Vite | Type-safe, fast HMR |
| Styling | Tailwind CSS 3 | Rapid UI without context-switching |
| Charts | Recharts | Lightweight React charting for histograms |
| Testing (BE) | pytest + pytest-django | Mirrors ref project test structure |
| Testing (FE) | Vitest + Testing Library | Fast, Vite-native |

---

## Data Model

```
Faction
  id, name, version, last_fetched

Unit
  id, faction FK, name, quality, defense, tough, points, special_rules JSON

Weapon
  id, name, range, attacks, attacks_string, ap, special_rules JSON

UnitWeaponSlot
  id, unit FK, weapon FK, is_default, upgrade_cost

ArmyList
  id, name, faction FK, point_limit, created_at, updated_at

ListUnit
  id, army_list FK, unit FK, model_count, selected_weapon_slot FK, notes
```

---

## Calculation Engine (core math)

```python
# Probability primitives — all pure functions, no Django dependencies
def p_hit(quality: float, modifiers: float = 0) -> float:
    """Probability a single attack die hits."""
    return (7 - max(2, min(6, quality + modifiers))) / 6

def p_fail_defense(defense: float, ap: float) -> float:
    """Probability a single defense die fails."""
    target = max(2, defense - ap)
    return 1 - (7 - target) / 6  # clamp: if target > 6 returns 1.0

def expected_wounds(attacks: float, quality: float, defense: float,
                    ap: float, deadly: int = 1) -> float:
    return attacks * p_hit(quality) * p_fail_defense(defense, ap) * deadly

def wound_distribution(attacks: int, quality: float, defense: float,
                       ap: float, deadly: int = 1) -> list[float]:
    """Exact probability distribution over wound counts [0..attacks*deadly].
    Uses binomial convolution for compound probability."""
    ...
```

Special rules applied as decorator functions wrapping the base calc (same pattern
as `abilities.py` in the ref project).

---

## Step 1 — Skeleton project setup

**Context**: Empty repo with only a `refs/` folder and a `.git`. Nothing else exists.

**Tasks**:
- [ ] `django-admin startproject opr_helper backend/`
- [ ] `pip install django djangorestframework django-cors-headers pytest pytest-django`
- [ ] Create `backend/requirements.txt` and `backend/.env.example`
- [ ] `npm create vite@latest frontend -- --template react-ts`
- [ ] `npm install tailwindcss recharts axios react-router-dom`
- [ ] Configure `tailwind.config.js` and `postcss.config.js`
- [ ] Add `Makefile` with `make dev-be`, `make dev-fe`, `make test`
- [ ] Add `.gitignore` entries for `__pycache__`, `.env`, `node_modules`, `dist`
- [ ] Add `README.md` with quick-start instructions

**Verification**:
```bash
cd backend && python manage.py runserver  # returns 200 on /
cd frontend && npm run dev               # Vite starts on :5173
```

**Exit criteria**: Both servers start without errors; no hardcoded secrets.

---

## Step 2 — AoF data models + migrations

**Context**: Django project created in Step 1. No models exist yet.

**Tasks**:
- [ ] Create Django apps: `army_books`, `lists`
- [ ] Define models in `army_books/models.py`:
  - `Faction(id, name, version, last_fetched)`
  - `Unit(id, faction, name, quality, defense, tough, points, special_rules)`
  - `Weapon(id, name, range, attacks, attacks_string, ap, special_rules)`
  - `UnitWeaponSlot(id, unit, weapon, is_default, upgrade_cost)`
- [ ] Define models in `lists/models.py`:
  - `ArmyList(id, name, faction, point_limit, created_at, updated_at)`
  - `ListUnit(id, army_list, unit, model_count, selected_weapon_slot, notes)`
- [ ] Run `makemigrations` and `migrate`
- [ ] Register all models in `admin.py` for each app
- [ ] Write unit tests for model creation and `__str__` methods

**Insight**: `special_rules` stored as `JSONField` rather than FK relations because
OPR publishes rules as key-value strings (e.g. `"Poison"`, `"Deadly(3)"`), and
the calculation engine parses them at runtime — avoids N+1 migration churn as rules
change between game versions.

**Verification**:
```bash
python manage.py test army_books lists  # all model tests pass
python manage.py check                  # no system errors
```

**Exit criteria**: Migrations clean; admin renders all models; tests green.

---

## Step 3 — OPR data integration (fetch + cache army books)

**Context**: Models exist (Step 2). Need real unit data.
OPR exposes army book data at `https://army-forge.onepagerules.com/api/army-books`
with JSON payloads containing faction name, units, weapons, upgrades.

**Tasks**:
- [ ] Create `army_books/opr_client.py` — thin HTTP client wrapping `requests`
  - `fetch_army_book_list() -> list[dict]`
  - `fetch_army_book(game_system: str, uid: str) -> dict`
- [ ] Create `army_books/management/commands/sync_army_books.py`
  - Django management command: `python manage.py sync_army_books`
  - Fetches all AoF army books, upserts into DB
  - Parses `quality`, `defense`, `tough`, weapon stats, special rules
  - Idempotent — re-running updates stale data without duplicating
- [ ] Create `army_books/parsers.py` — pure functions for OPR JSON → model kwargs
  - `parse_unit(raw: dict) -> dict`
  - `parse_weapon(raw: dict) -> dict`
  - `parse_special_rules(raw: list) -> dict`
- [ ] Write tests for `parsers.py` using fixture JSON (not live API calls)

**Insight**: Parsing quality/defense from OPR format: OPR stores stats as strings
like `"4+"`. Strip the `+` and cast to int. For variable attacks (`"A2"`, `"2d6"`),
store both the string form and the numeric EV — mirrors the `shots_string`/`shots`
dual-field pattern from the ref project's `Weapon` model.

**Verification**:
```bash
python manage.py sync_army_books  # completes without error
python manage.py shell -c "from army_books.models import Faction; print(Faction.objects.count())"  # > 0
python manage.py test army_books  # all tests pass
```

**Exit criteria**: At least one AoF faction with units and weapons in the DB.

---

## Step 4 — AoF calculation engine

**Context**: Data exists (Step 3). This step builds the pure Python probability engine.
The ref project's `calculations.py` pattern (injectable callables) is the model.

**Tasks**:
- [ ] Create `army_books/calc/` package:
  - `primitives.py` — `p_hit`, `p_fail_defense`, `expected_wounds`
  - `distribution.py` — `wound_distribution` (binomial exact or Monte Carlo fallback)
  - `specials.py` — callable modifiers for Poison, Rending, Deadly, Blast, Furious, etc.
  - `engine.py` — `calculate_ev(unit, weapon, target_stats, specials) -> float`
  - `engine.py` — `calculate_distribution(unit, weapon, target_stats, specials) -> list[float]`
- [ ] AoF math formulas:
  ```
  p_hit(quality) = (7 - clamp(quality, 2, 6)) / 6
  p_fail_defense(defense, ap) = 1 - (7 - clamp(defense-ap, 2, 6)) / 6
  ev = attacks * p_hit * p_fail_defense * deadly
  ```
- [ ] Special rule implementations:
  - **Poison**: 1/6 of attacks auto-wound; remaining 5/6 go through normal flow
  - **Rending**: 1/6 attacks treated as AP6, rest use weapon's AP
  - **Deadly(X)**: multiply each wound by X in distribution
  - **Blast(X)**: replace attacks roll with constant X hits
  - **Furious**: expected extra attacks = (1/6) × base_attacks (recursive)
  - **Stealth**: quality +1 for attacker (harder to hit)
  - **Indirect**: quality +1 for attacker
- [ ] Write comprehensive pytest unit tests with parametrized cases:
  - Basic EV: QU4, DE4, AP0, A3 → expected = 3 × (3/6) × (3/6) = 0.75
  - AP effect: same but AP2, DE4 → defend on 6+ → fail rate = 5/6 → EV = 3 × 0.5 × (5/6)
  - Poison interaction
  - Rending interaction
  - Deadly multiplication

**Insight**: For `wound_distribution`, use exact binomial convolution rather than
Monte Carlo where attacks ≤ 20 (nearly all AoF units). This gives precise P(kill)
values without sampling noise. For Deadly(X), convolve the wound distribution with
multiplication: each wound outcome becomes `wounds × X`. Use `numpy` for convolution
efficiency (already in ref project dependencies).

**Verification**:
```bash
pytest army_books/calc/ -v  # all calc unit tests green
python -c "from army_books.calc.engine import calculate_ev; print(calculate_ev(4,4,0,3,1))"
# Should print 0.75
```

**Exit criteria**: All special rules implemented and tested; zero import of Django models
in `calc/` package (pure Python, testable without DB).

---

## Step 5 — REST API endpoints

**Context**: Calculation engine done (Step 4). Need HTTP layer for the frontend.

**Tasks**:
- [ ] Install `djangorestframework` and configure in `settings.py`
- [ ] Create `army_books/serializers.py`:
  - `FactionSerializer`, `UnitSerializer`, `WeaponSerializer`
- [ ] Create `army_books/views.py`:
  - `GET /api/factions/` — list all factions
  - `GET /api/factions/<id>/units/` — units for a faction
  - `GET /api/units/<id>/` — single unit with weapons
- [ ] Create `lists/serializers.py`:
  - `ArmyListSerializer`, `ListUnitSerializer`
- [ ] Create `lists/views.py` — full CRUD:
  - `GET/POST /api/lists/`
  - `GET/PATCH/DELETE /api/lists/<id>/`
  - `POST /api/lists/<id>/units/` — add unit
  - `DELETE /api/lists/<id>/units/<list_unit_id>/`
- [ ] Create `army_books/views.py` — calculation endpoint:
  - `POST /api/calc/ev/`
    ```json
    { "unit_id": 1, "weapon_id": 2, "target": {"defense": 4, "tough": 1},
      "target_range": 12 }
    ```
    Returns `{ "ev": 1.25, "distribution": [0.1, 0.3, 0.4, 0.2] }`
- [ ] Configure `django-cors-headers` to allow `localhost:5173`
- [ ] Write API tests using DRF's `APITestCase`

**Verification**:
```bash
python manage.py test  # all backend tests pass
curl localhost:8000/api/factions/ | python -m json.tool  # valid JSON list
curl -X POST localhost:8000/api/calc/ev/ -H "Content-Type: application/json" \
  -d '{"unit_id":1,"weapon_id":1,"target":{"defense":4,"tough":1},"target_range":12}'
```

**Exit criteria**: All CRUD endpoints respond correctly; calc endpoint returns EV and
distribution array; no 500 errors on any endpoint.

---

## Step 6 — Frontend: army list builder

**Context**: API is live (Step 5). Build the React army builder UI.

**Tasks**:
- [ ] Set up React Router with routes:
  - `/` — home / faction browser
  - `/factions/:id` — faction unit list
  - `/lists` — my army lists
  - `/lists/:id` — army list builder
  - `/calc` — standalone unit calculator
- [ ] Create API client `src/api/client.ts` using Axios with base URL config
- [ ] Create `src/api/hooks.ts` — React Query hooks:
  - `useFactions()`, `useUnits(factionId)`, `useLists()`, `useList(id)`
- [ ] Build components:
  - `FactionCard` — faction name + unit count + "Browse" CTA
  - `UnitCard` — unit stats in clean card: name, QU, DE, T, pts, weapon pills
  - `ListBuilder` — split view: left panel unit browser, right panel list
  - `ListPointTracker` — running total vs limit, color-coded at 100%
  - `ListUnitRow` — unit in list with model count stepper and remove button
- [ ] Persist list to backend on every change (debounced PATCH)
- [ ] Show validation errors (over point limit, illegal model counts)

**Design**: Clean light-mode card grid with intentional hierarchy. Faction browser
uses large typography + faction art placeholder. List builder uses two-column split.
Unit cards show QU/DE/T as colored badges. Points tracker is a sticky header bar.

**Verification**:
- Browse factions → select one → see unit list
- Click "Add to List" → unit appears in list panel with model count
- Change model count → points update immediately
- Exceeding limit → tracker turns red, save blocked

**Exit criteria**: Can build a complete army list and save it; points track correctly;
no console errors.

---

## Step 7 — Frontend: probability calculator + visualization

**Context**: Army builder works (Step 6). Add the probability/EV feature.

**Tasks**:
- [ ] Create `src/api/hooks.ts` additions:
  - `useCalcEV(params)` — POST to `/api/calc/ev/`, reactive to param changes
- [ ] Build `CalcPage` at `/calc`:
  - Left panel: attacker selector (faction → unit → weapon)
  - Center panel: target selector (preset profiles OR custom QU/DE/T inputs)
    - Presets: "Light Infantry (QU4 DE5 T1)", "Heavy Infantry (QU3 DE3 T3)",
      "Monster (QU3 DE2 T10)", "Custom..."
  - Right panel: results
    - Large EV number with "expected wounds" label
    - Probability histogram (Recharts BarChart)
      - X-axis: wound count
      - Y-axis: probability (%)
    - Derived stats: P(kill model), P(kill unit), P(zero wounds)
- [ ] Add calculator access from army list: click any unit → opens calc pre-filled
- [ ] Add "Army vs Target" view on list page:
  - For each unit in list, show EV bar (horizontal bar chart per unit)
  - Sort by wounds/point efficiency
- [ ] Responsive layout: single column on mobile, two-column on desktop

**Insight**: For probability histograms, show both the distribution bars AND a
vertical line at the expected value — this makes the concept of "EV vs variance" 
immediately visual. High-variance units (Blast, variable attacks) will have flat
wide distributions vs low-variance units that cluster tightly around the mean.
This is the key educational value for competitive players.

**Verification**:
- Select attacker + target → histogram renders with correct shape
- Changing AP → distribution shifts right (more wounds)
- Blast unit → distribution is spiky at fixed value
- Army view → all units show efficiency bars

**Exit criteria**: Histogram renders correct distribution; EV matches back-end calc;
P(kill) values are mathematically consistent with distribution.

---

## Step 8 — Army analysis dashboard

**Context**: Calculator and list builder work (Steps 6–7). Add high-level
strategic analysis.

**Tasks**:
- [ ] Add `GET /api/lists/<id>/analysis/` endpoint:
  - For each unit in list, calculate EV against 3 standard targets:
    - "Infantry" (QU4, DE5, T1)
    - "Elite" (QU3, DE3, T3)
    - "Monster" (QU3, DE2, T10)
  - Return wounds/point for each unit × target combination
  - Return list totals: offensive score, point efficiency
- [ ] Build `AnalysisDashboard` component on list page (tab or expandable section):
  - Heatmap table: rows = units, columns = target profiles, cells = EV color-coded
    - Green = efficient, red = weak, white = average
  - "Best vs Infantry" / "Best vs Monsters" callout cards
  - List-level summary: offensive balance score
- [ ] Add "Share List" feature: generate a read-only URL with list encoded in query params
  - Pure client-side: serialize list to base64 JSON in URL
  - No auth required for sharing

**Verification**:
- Open analysis tab → heatmap renders for all units
- Unit with Deadly(2) → shows 2× cells compared to base unit
- Share link → opens in incognito with correct list

**Exit criteria**: Heatmap renders correctly; wounds/point values match calculator;
share links work without login.

---

## Dependency Graph

```
Step 1 (Setup)
  └─ Step 2 (Models)
       └─ Step 3 (OPR Data Sync)
            ├─ Step 4 (Calc Engine)  ← can start from Step 2 in parallel
            └─ Step 5 (REST API)     ← depends on Steps 3 + 4
                 ├─ Step 6 (Army Builder UI)
                 └─ Step 7 (Calculator UI)  ← depends on Step 6 (router)
                      └─ Step 8 (Analysis)
```

**Parallelism opportunity**: Steps 3 and 4 can be developed in parallel after Step 2.
Step 4 (calc engine) has zero DB dependencies — it's pure Python testable immediately.

---

## Invariants (must hold after every step)

1. `python manage.py check` passes — no Django system errors
2. `pytest` passes — no regressions
3. `npm run type-check` passes — no TypeScript errors
4. No hardcoded API keys, passwords, or tokens
5. Calc engine functions have no Django imports (pure Python, importable anywhere)
6. All API endpoints return consistent `{data, error}` envelope

---

## Open Questions (resolve before Step 3)

1. **OPR API auth**: Does the army-forge API require a key, or is it public?
   Check `https://army-forge.onepagerules.com/api/army-books?gameSystemSlug=age-of-fantasy`
2. **Upgrades support**: OPR units have upgrade options (e.g., swap weapon for +5pts).
   v1 can skip upgrades and only show default loadouts — add upgrades in a v2.
3. **Persistence strategy**: Anonymous lists (localStorage) vs user accounts?
   Recommend: start with localStorage + optional save-to-server for v1.
