from rest_framework import serializers

from army_books.models import UnitWeaponSlot
from lists.models import ArmyList, ListUnit


class ListUnitSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    unit_points = serializers.IntegerField(source="unit.points", read_only=True)
    selected_weapon_name = serializers.CharField(
        source="selected_weapon_slot.weapon.name",
        read_only=True,
        allow_null=True,
    )
    total_points = serializers.SerializerMethodField()

    class Meta:
        model = ListUnit
        fields = (
            "id",
            "unit",
            "unit_name",
            "unit_points",
            "model_count",
            "selected_weapon_slot",
            "selected_weapon_name",
            "notes",
            "total_points",
        )

    def get_total_points(self, obj):
        return obj.unit.points * obj.model_count

    def validate(self, attrs):
        unit = attrs.get("unit") or getattr(self.instance, "unit", None)
        slot = attrs.get("selected_weapon_slot")
        if slot and unit and slot.unit_id != unit.id:
            raise serializers.ValidationError("Selected weapon slot must belong to the unit.")
        return attrs


class ArmyListSerializer(serializers.ModelSerializer):
    units = ListUnitSerializer(many=True, read_only=True)
    total_points = serializers.SerializerMethodField()

    class Meta:
        model = ArmyList
        fields = (
            "id",
            "name",
            "faction",
            "point_limit",
            "created_at",
            "updated_at",
            "units",
            "total_points",
        )

    def get_total_points(self, obj):
        entries = getattr(obj, "units", None)
        if entries is None:
            return 0
        return sum(entry.unit.points * entry.model_count for entry in entries.all())


class AddListUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListUnit
        fields = ("unit", "model_count", "selected_weapon_slot", "notes")

    def validate_selected_weapon_slot(self, value: UnitWeaponSlot | None):
        if value is not None and value.unit_id != int(self.initial_data.get("unit")):
            raise serializers.ValidationError("Selected weapon slot must belong to the unit.")
        return value
