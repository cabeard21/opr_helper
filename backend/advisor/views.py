import re

from django.db import transaction
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from advisor.llm_service import (
    AdvisorLLMError,
    ListSuggestion,
    get_default_model,
    get_default_provider,
    suggest_list,
)
from advisor.rate_limit import advisor_rate_limit_exceeded
from advisor.reconciliation import ReconciledSuggestion, reconcile_suggestion
from army_books.models import Faction, Unit
from lists.models import ArmyList, ListUnit, ListUnitUpgrade
from lists.serializers import ArmyListSerializer
from lists.validation import army_list_validation, selected_or_default_slot


def envelope(data=None, error=None, status_code=status.HTTP_200_OK):
    return Response({"data": data, "error": error}, status=status_code)


@api_view(["GET"])
def advisor_status(_request):
    return envelope(
        {
            "status": "advisor-ready",
            "provider": get_default_provider(),
            "model": get_default_model(),
        }
    )


@api_view(["POST"])
def suggest_army_list(request):
    payload, error = _validate_suggestion_request(request.data)
    if error is not None:
        return envelope(error=error, status_code=status.HTTP_400_BAD_REQUEST)

    try:
        faction = Faction.objects.get(id=payload["faction_id"])
    except Faction.DoesNotExist:
        return envelope(error="Faction not found.", status_code=status.HTTP_404_NOT_FOUND)

    if payload["suggestion"] is None and advisor_rate_limit_exceeded(request):
        return envelope(
            error="Too many advisor requests. Try again shortly.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if payload["suggestion"] is not None:
        suggestion = payload["suggestion"]
    else:
        try:
            suggestion = suggest_list(payload["faction_id"], payload["point_limit"], payload["prompt"])
        except AdvisorLLMError:
            return envelope(error="Advisor provider unavailable.", status_code=status.HTTP_502_BAD_GATEWAY)

    reconciled = reconcile_suggestion(
        faction=faction,
        point_limit=payload["point_limit"],
        suggestion=suggestion,
    )
    if payload["suggestion"] is None:
        correction_feedback = _advisor_correction_feedback(
            reconciled=reconciled,
            point_limit=payload["point_limit"],
        )
        if correction_feedback:
            try:
                retry_suggestion = suggest_list(
                    payload["faction_id"],
                    payload["point_limit"],
                    payload["prompt"],
                    correction_feedback=correction_feedback,
                )
            except AdvisorLLMError:
                retry_suggestion = None
            if retry_suggestion is not None:
                retry_reconciled = reconcile_suggestion(
                    faction=faction,
                    point_limit=payload["point_limit"],
                    suggestion=retry_suggestion,
                )
                if _prefer_retry_reconciliation(reconciled, retry_reconciled):
                    reconciled = retry_reconciled

    if not payload["dry_run"] and not reconciled.suggestion.units:
        return envelope(
            data=_response_data(reconciled=reconciled, army_list=None),
            error="No valid suggested units were returned by the advisor.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    army_list = None
    response_status = status.HTTP_200_OK
    if not payload["dry_run"]:
        with transaction.atomic():
            army_list = _create_army_list(
                faction=faction,
                point_limit=payload["point_limit"],
                user_prompt=payload["prompt"],
                suggestion=reconciled.suggestion,
            )
            validation = army_list_validation(army_list)
            if validation["errors"]:
                army_list.delete()
                return envelope(
                    data=_response_data(reconciled=reconciled, army_list=None),
                    error={
                        "list": "Advisor suggestion could not produce a legal army list.",
                        "validation": validation["errors"],
                    },
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
        response_status = status.HTTP_201_CREATED

    return envelope(
        data=_response_data(reconciled=reconciled, army_list=army_list),
        status_code=response_status,
    )


def _validate_suggestion_request(data):
    try:
        faction_id = int(data.get("faction"))
    except (TypeError, ValueError):
        return None, {"faction": "Faction is required and must be an integer."}

    try:
        point_limit = int(data.get("point_limit"))
    except (TypeError, ValueError):
        return None, {"point_limit": "Point limit is required and must be an integer."}

    prompt = data.get("prompt")
    if point_limit <= 0:
        return None, {"point_limit": "Point limit must be positive."}
    if not isinstance(prompt, str) or not prompt.strip():
        return None, {"prompt": "Prompt is required."}
    if len(prompt) > 2000:
        return None, {"prompt": "Prompt must be at most 2000 characters."}

    suggestion, suggestion_error = _parse_submitted_suggestion(data.get("suggestion"))
    if suggestion_error is not None:
        return None, suggestion_error

    return {
        "faction_id": faction_id,
        "point_limit": point_limit,
        "prompt": prompt.strip(),
        "dry_run": _parse_bool(data.get("dry_run", True)),
        "suggestion": suggestion,
    }, None


def _parse_submitted_suggestion(raw_suggestion):
    if raw_suggestion in (None, ""):
        return None, None
    try:
        return ListSuggestion.model_validate(raw_suggestion), None
    except ValidationError as exc:
        return None, {"suggestion": exc.errors()}


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)


def _response_data(
    *,
    reconciled: ReconciledSuggestion,
    army_list: ArmyList | None,
):
    return {
        "suggestion": reconciled.suggestion.model_dump(),
        "computed_total_points": reconciled.computed_total_points,
        "point_delta": reconciled.point_delta,
        "reconciliation_warnings": reconciled.warnings,
        "army_list": ArmyListSerializer(army_list).data if army_list else None,
    }


def _advisor_correction_feedback(
    *,
    reconciled: ReconciledSuggestion,
    point_limit: int,
) -> str:
    avoidable_warnings = [
        warning
        for warning in reconciled.warnings
        if any(
            marker in warning.lower()
            for marker in (
                "unknown",
                "not available",
                "ignored invalid",
                "skipped",
                "model count was",
                "to use remaining points",
            )
        )
    ]
    underfilled = point_limit > 0 and 0 < reconciled.computed_total_points < point_limit * 0.9
    if not avoidable_warnings and not underfilled:
        return ""

    feedback: list[str] = []
    if avoidable_warnings:
        feedback.append("Avoid these validation/reconciliation changes:")
        feedback.extend(f"- {warning}" for warning in avoidable_warnings[:8])
    if underfilled:
        feedback.append(
            f"Spend closer to {point_limit} points; the prior legal total was "
            f"{reconciled.computed_total_points}."
        )
    return "\n".join(feedback)


def _prefer_retry_reconciliation(
    original: ReconciledSuggestion,
    retry: ReconciledSuggestion,
) -> bool:
    if retry.suggestion.units and not original.suggestion.units:
        return True
    if not retry.suggestion.units:
        return False
    retry_delta = abs(retry.point_delta)
    original_delta = abs(original.point_delta)
    retry_warnings = len(retry.warnings)
    original_warnings = len(original.warnings)
    if retry_delta <= original_delta and retry_warnings <= original_warnings:
        return retry_delta < original_delta or retry_warnings < original_warnings
    return False


def _create_army_list(
    *,
    faction: Faction,
    point_limit: int,
    user_prompt: str,
    suggestion: ListSuggestion,
) -> ArmyList:
    army_list = ArmyList.objects.create(
        name=_advisor_list_name(
            faction=faction,
            point_limit=point_limit,
            suggestion=suggestion,
        ),
        faction=faction,
        point_limit=point_limit,
        advisor_archetype=suggestion.archetype,
        advisor_playstyle=suggestion.playstyle,
        advisor_strategy_summary=suggestion.strategy_summary,
        advisor_prompt=user_prompt,
        advisor_warnings=suggestion.warnings,
    )
    entries: list[ListUnit | None] = []
    for suggested_unit in suggestion.units:
        try:
            unit = Unit.objects.prefetch_related("weapon_slots__weapon").get(
                id=suggested_unit.unit_id,
                faction=faction,
            )
        except Unit.DoesNotExist:
            entries.append(None)
            continue
        entry = ListUnit.objects.create(
            army_list=army_list,
            unit=unit,
            model_count=suggested_unit.model_count,
            notes=suggested_unit.justification,
        )
        entry.selected_weapon_slot = selected_or_default_slot(entry)
        entry.save(update_fields=["selected_weapon_slot"])
        ListUnitUpgrade.objects.bulk_create(
            [
                ListUnitUpgrade(list_unit=entry, option_id=option_id)
                for option_id in suggested_unit.selected_upgrade_ids
            ]
        )
        entries.append(entry)
    for index, suggested_unit in enumerate(suggestion.units):
        parent_index = suggested_unit.parent_unit_index
        if parent_index is None or index >= len(entries):
            continue
        entry = entries[index]
        parent_entry = entries[parent_index] if parent_index < len(entries) else None
        if entry is None or parent_entry is None:
            continue
        entry.parent_entry = parent_entry
        entry.save(update_fields=["parent_entry"])
    return army_list


def _advisor_list_name(
    *,
    faction: Faction,
    point_limit: int,
    suggestion: ListSuggestion,
) -> str:
    archetype = _clean_name_part(suggestion.archetype)
    descriptor = archetype or "Advisor List"
    name = _clean_name_part(f"{faction.name} - {descriptor} ({point_limit} pts)")
    max_length = ArmyList._meta.get_field("name").max_length or 160
    return name[:max_length]


def _clean_name_part(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
