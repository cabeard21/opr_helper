from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from lists.analysis import analyze_army_list, validate_targets
from lists.exporters import ArmyForgeExportError, army_forge_save_json
from lists.models import ArmyList, ListUnit
from lists.serializers import AddListUnitSerializer, ArmyListSerializer, ListUnitSerializer
from lists.validation import validate_parent_entry


def envelope(data=None, error=None, status_code=status.HTTP_200_OK):
    return Response({"data": data, "error": error}, status=status_code)


def _list_queryset():
    return ArmyList.objects.select_related("faction").prefetch_related(
        "units__unit",
        "units__unit__weapon_slots__weapon",
        "units__unit__upgrade_sections__options__weapons",
        "units__selected_weapon_slot__weapon",
        "units__selected_upgrades__option__section",
        "units__selected_upgrades__option__weapons",
        "units__parent_entry__unit",
    )


@api_view(["GET", "POST"])
def army_lists(request):
    if request.method == "GET":
        return envelope(ArmyListSerializer(_list_queryset(), many=True).data)

    serializer = ArmyListSerializer(data=request.data)
    if not serializer.is_valid():
        return envelope(None, serializer.errors, status.HTTP_400_BAD_REQUEST)
    army_list = serializer.save()
    return envelope(
        ArmyListSerializer(_list_queryset().get(id=army_list.id)).data,
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
def army_list_detail(request, list_id: int):
    try:
        army_list = _list_queryset().get(id=list_id)
    except ArmyList.DoesNotExist:
        return envelope(None, "Army list not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return envelope(ArmyListSerializer(army_list).data)

    if request.method == "DELETE":
        army_list.delete()
        return envelope({"deleted": True})

    serializer = ArmyListSerializer(army_list, data=request.data, partial=True)
    if not serializer.is_valid():
        return envelope(None, serializer.errors, status.HTTP_400_BAD_REQUEST)
    army_list = serializer.save()
    return envelope(ArmyListSerializer(_list_queryset().get(id=army_list.id)).data)


@api_view(["POST"])
def add_list_unit(request, list_id: int):
    try:
        army_list = ArmyList.objects.get(id=list_id)
    except ArmyList.DoesNotExist:
        return envelope(None, "Army list not found.", status.HTTP_404_NOT_FOUND)

    serializer = AddListUnitSerializer(data=request.data)
    if not serializer.is_valid():
        return envelope(None, serializer.errors, status.HTTP_400_BAD_REQUEST)

    unit = serializer.validated_data["unit"]
    if unit.faction_id != army_list.faction_id:
        return envelope(
            None,
            "List units must belong to the same faction as the army list.",
            status.HTTP_400_BAD_REQUEST,
        )
    parent_entry = serializer.validated_data.get("parent_entry")
    if parent_entry is not None:
        candidate = ListUnit(
            army_list=army_list,
            unit=unit,
            model_count=serializer.validated_data.get("model_count", unit.default_models),
            parent_entry=parent_entry,
        )
        parent_error = validate_parent_entry(candidate, parent_entry)
        if parent_error:
            return envelope(None, parent_error, status.HTTP_400_BAD_REQUEST)

    serializer.save(army_list=army_list)
    return envelope(
        ArmyListSerializer(_list_queryset().get(id=army_list.id)).data,
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
def remove_list_unit(request, list_id: int, list_unit_id: int):
    try:
        army_list = ArmyList.objects.get(id=list_id)
    except ArmyList.DoesNotExist:
        return envelope(None, "Army list not found.", status.HTTP_404_NOT_FOUND)

    try:
        list_unit = ListUnit.objects.get(id=list_unit_id, army_list=army_list)
    except ListUnit.DoesNotExist:
        return envelope(None, "List unit not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "PATCH":
        serializer = ListUnitSerializer(list_unit, data=request.data, partial=True)
        if not serializer.is_valid():
            return envelope(None, serializer.errors, status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return envelope(ArmyListSerializer(_list_queryset().get(id=army_list.id)).data)

    list_unit.delete()
    return envelope(ArmyListSerializer(_list_queryset().get(id=army_list.id)).data)


@api_view(["POST"])
def army_list_analysis(request, list_id: int):
    try:
        army_list = _list_queryset().get(id=list_id)
    except ArmyList.DoesNotExist:
        return envelope(None, "Army list not found.", status.HTTP_404_NOT_FOUND)

    targets, error = validate_targets(request.data.get("targets"))
    if error:
        return envelope(None, error, status.HTTP_400_BAD_REQUEST)

    return envelope(analyze_army_list(army_list, targets))


@api_view(["GET"])
def army_list_army_forge_export(_request, list_id: int):
    try:
        army_list = _list_queryset().get(id=list_id)
    except ArmyList.DoesNotExist:
        return envelope(None, "Army list not found.", status.HTTP_404_NOT_FOUND)

    try:
        return envelope(army_forge_save_json(army_list))
    except ArmyForgeExportError as error:
        return envelope(None, str(error), status.HTTP_422_UNPROCESSABLE_ENTITY)
