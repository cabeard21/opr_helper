from __future__ import annotations

from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from army_books.calc.engine import calculate_distribution, calculate_ev
from army_books.models import Faction, Unit, Weapon
from army_books.serializers import FactionSerializer, UnitSerializer


def envelope(data=None, error=None, status_code=status.HTTP_200_OK):
    return Response({"data": data, "error": error}, status=status_code)


@api_view(["GET"])
def faction_list(_request):
    factions = Faction.objects.annotate(unit_count=Count("units")).order_by("name")
    return envelope(FactionSerializer(factions, many=True).data)


@api_view(["GET"])
def faction_units(_request, faction_id: int):
    try:
        faction = Faction.objects.get(id=faction_id)
    except Faction.DoesNotExist:
        return envelope(None, "Faction not found.", status.HTTP_404_NOT_FOUND)

    units = (
        faction.units.prefetch_related("weapon_slots__weapon")
        .all()
        .order_by("name")
    )
    return envelope(UnitSerializer(units, many=True).data)


@api_view(["GET"])
def unit_detail(_request, unit_id: int):
    try:
        unit = Unit.objects.prefetch_related("weapon_slots__weapon").get(id=unit_id)
    except Unit.DoesNotExist:
        return envelope(None, "Unit not found.", status.HTTP_404_NOT_FOUND)

    return envelope(UnitSerializer(unit).data)


@api_view(["POST"])
def calculate_ev_view(request):
    unit_id = request.data.get("unit_id")
    weapon_id = request.data.get("weapon_id")
    target = request.data.get("target") or {}
    modifiers = request.data.get("modifiers") or {}

    try:
        unit = Unit.objects.get(id=unit_id)
    except Unit.DoesNotExist:
        return envelope(None, "Unit not found.", status.HTTP_404_NOT_FOUND)

    try:
        weapon = Weapon.objects.get(id=weapon_id)
    except Weapon.DoesNotExist:
        return envelope(None, "Weapon not found.", status.HTTP_404_NOT_FOUND)

    try:
        target_defense = int(target["defense"])
        target_tough = int(target.get("tough", 1))
    except (KeyError, TypeError, ValueError):
        return envelope(
            None,
            "Target defense and tough must be valid integers.",
            status.HTTP_400_BAD_REQUEST,
        )

    special_rules = {**unit.special_rules, **weapon.special_rules}
    ev = calculate_ev(
        weapon.attacks,
        unit.quality,
        target_defense,
        weapon.ap,
        special_rules,
        modifiers=modifiers,
    )
    distribution = calculate_distribution(
        weapon.attacks,
        unit.quality,
        target_defense,
        weapon.ap,
        special_rules,
        modifiers=modifiers,
    )
    p_zero = _probability_at_least(distribution, 0)
    p_kill = _probability_at_least(distribution, target_tough)

    return envelope(
        {
            "ev": round(ev, 6),
            "distribution": distribution,
            "p_zero_wounds": round(p_zero, 6),
            "p_kill_model": round(p_kill, 6),
            "p_kill_unit": round(p_kill, 6),
        }
    )


def _probability_at_least(
    distribution: list[dict[str, float | int]],
    threshold: int,
) -> float:
    if threshold <= 0:
        return sum(
            point["probability"]
            for point in distribution
            if int(point["wounds"]) == 0
        )
    return sum(
        point["probability"]
        for point in distribution
        if int(point["wounds"]) >= threshold
    )
