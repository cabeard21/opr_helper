from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from lists.analysis import analyze_army_list, validate_targets
from lists.models import ArmyList, ListUnit
from lists.serializers import AddListUnitSerializer, ArmyListSerializer, ListUnitSerializer


def envelope(data=None, error=None, status_code=status.HTTP_200_OK):
    return Response({"data": data, "error": error}, status=status_code)


def _list_queryset():
    return ArmyList.objects.select_related("faction").prefetch_related(
        "units__unit",
        "units__unit__weapon_slots__weapon",
        "units__selected_weapon_slot__weapon",
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
