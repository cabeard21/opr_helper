# AoF Special Rules Implementation Coverage

Source: `refs/AoF - Advanced Rules v3.5.1 - Print Friendly.pdf`, printed pages 13-14.

Coverage scale:

- High: mechanically modeled in core app behavior.
- Partial: approximated, context-limited, or used only in advisor/list scoring.
- Metadata: stored, parsed, displayed, or exposed to prompts, but not mechanically resolved.
- None: no meaningful app behavior found.

Primary implementation seams:

- Combat math: `backend/army_books/calc/engine.py`
- Rules parsing: `backend/army_books/parsers.py`
- List validation: `backend/lists/validation.py`
- List analysis: `backend/lists/analysis.py`
- Advisor scoring/packages: `backend/advisor/unit_scorer.py`, `backend/advisor/packages.py`
- Frontend list analysis and display: `frontend/src/pages/ListBuilderPage.tsx`, `frontend/src/components/UnitCard.tsx`

| Rule | Coverage | Current app behavior / gap |
|---|---:|---|
| Sergeant | Partial | Extra hit on natural 6 is modeled when the rule is present; command-group upgrade limits are not modeled. |
| Musician | Metadata | No movement bonus. |
| Banner | Metadata | No morale bonus; can appear as upgrade label/context. |
| Ambush | Partial | Advisor/list-role mobility signal only; no reserve/deployment/objective restriction. |
| AP(X) | High | Parsed into `weapon.ap` and applied in EV math. Caveat: defense auto-success-on-6 edge is not modeled. |
| Artillery | None | No Hold-only, long-range hit bonus, or incoming penalty. |
| Bane | Partial | Ignores target Regeneration; missing forced reroll of unmodified Defense 6s. |
| Blast(X) | Partial | Included in EV, but simplified as fixed attack count and no hit roll; missing per-hit multiplication, target model cap, and cover behavior. |
| Caster(X) | None | No spell tokens or spell casting system. |
| Counter | None | No strikes-first or Impact reduction. |
| Deadly(X) | High | Wound multiplication and distribution modeled; wound assignment/no-carryover details are not. |
| Fast | Partial | Advisor/list-health mobility signal; no movement simulation. |
| Fear(X) | None | No melee-result modifier. |
| Fearless | Partial | Advisor support/flag only; no morale reroll/pass mechanic. |
| Flying | Partial | Advisor/list-health mobility signal; no terrain/unit movement handling. |
| Furious | Partial | Extra hit on natural 6 is modeled only when combat context is charging; full melee engagement flow is not modeled. |
| Hero | Partial | Embedding legality/UI/advisor support implemented; morale and wound-allocation details are not. |
| Immobile | None | No Hold-only restriction. |
| Impact(X) | Partial | Charge impact dice are modeled as AP0 hits when combat context is charging; fatigue and full movement/charge flow are not modeled. |
| Indirect | Partial | Calc UI can apply a -1 hit modifier; no LOS/cover/after-moving context. |
| Limited | None | No once-per-game tracking. |
| Regeneration | High | Defender-side wound ignore modeled as `2/3` wound multiplier; durability scoring uses `1.5`; Bane/Rending bypass handled. |
| Relentless | Partial | Extra hit on unmodified shooting 6s is modeled when combat context marks the target as over 9"; full range/line-of-sight flow is not modeled. |
| Reliable | None | Stored, but attacks are not changed to Quality 2+. |
| Rending | High | All Rending hits ignore Regeneration; natural 6 hits get exact AP(+4). |
| Scout | Partial | Advisor/list-health mobility signal; no deployment behavior. |
| Slow | None | No movement penalty. |
| Stealth | Partial | Calc UI can apply -1 hit modifier; advisor support flag exists; no range/all-model targeting automation. |
| Strider | Partial | Advisor/list-health mobility signal; no terrain rules. |
| Surge | High | Extra hit on natural 6 is modeled; only the original hit counts as a natural 6 for other special rules. |
| Takedown | None | No individual model targeting. |
| Thrust | Partial | Charge-only melee +1 to hit and AP(+1) are modeled through combat context; full charge flow is not modeled. |
| Tough(X) | High | Parsed into `unit.tough`, used for durability and kill thresholds; mixed-model wound allocation is not fully modeled. |
| Unstoppable | Partial | Ignores target Regeneration and negative hit modifiers in combat math; broader rule interactions outside the calculator are not modeled. |

Summary:

- Strongest modeled rules: AP, Deadly, Regeneration, Rending, Surge, Tough.
- Partially modeled combat rules: Bane, Blast, Furious, Impact, Indirect, Relentless, Sergeant, Stealth, Thrust, Unstoppable.
- Strategic/advisor-only signals: Ambush, Fast, Fearless, Flying, Scout, Strider, plus support tagging for Regeneration and Stealth.
- Mostly absent categories: movement/deployment simulation, morale, spells, terrain interaction, once-per-game tracking, individual model targeting, and charge-only context.
