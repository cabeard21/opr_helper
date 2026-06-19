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
from lists.models import ArmyList, ListUnit
from lists.serializers import ArmyListSerializer
from lists.validation import selected_or_default_slot


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

    if advisor_rate_limit_exceeded(request):
        return envelope(
            error="Too many advisor requests. Try again shortly.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        suggestion = suggest_list(payload["faction_id"], payload["point_limit"], payload["prompt"])
    except AdvisorLLMError as exc:
        return envelope(error="Advisor provider unavailable.", status_code=status.HTTP_502_BAD_GATEWAY)

    reconciled = reconcile_suggestion(
        faction=faction,
        point_limit=payload["point_limit"],
        suggestion=suggestion,
    )

    if not payload["dry_run"] and not reconciled.suggestion.units:
        return envelope(
            data=_response_data(reconciled=reconciled, army_list=None),
            error="No valid suggested units were returned by the advisor.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    army_list = None
    response_status = status.HTTP_200_OK
    if not payload["dry_run"]:
        army_list = _create_army_list(
            faction=faction,
            point_limit=payload["point_limit"],
            suggestion=reconciled.suggestion,
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

    return {
        "faction_id": faction_id,
        "point_limit": point_limit,
        "prompt": prompt.strip(),
        "dry_run": _parse_bool(data.get("dry_run", True)),
    }, None


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


def _create_army_list(
    *,
    faction: Faction,
    point_limit: int,
    suggestion: ListSuggestion,
) -> ArmyList:
    army_list = ArmyList.objects.create(
        name=f"Advisor Suggestion - {faction.name}",
        faction=faction,
        point_limit=point_limit,
    )
    for suggested_unit in suggestion.units:
        try:
            unit = Unit.objects.prefetch_related("weapon_slots__weapon").get(
                id=suggested_unit.unit_id,
                faction=faction,
            )
        except Unit.DoesNotExist:
            continue
        entry = ListUnit.objects.create(
            army_list=army_list,
            unit=unit,
            model_count=suggested_unit.model_count,
            notes=suggested_unit.justification,
        )
        entry.selected_weapon_slot = selected_or_default_slot(entry)
        entry.save(update_fields=["selected_weapon_slot"])
    return army_list
