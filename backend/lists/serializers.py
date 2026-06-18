from rest_framework import serializers

from army_books.models import UnitWeaponSlot
from lists.models import ArmyList, ListUnit
from lists.validation import army_list_points, army_list_validation, list_unit_points, validate_model_count


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
        return list_unit_points(obj)

    def validate(self, attrs):
        unit = attrs.get("unit") or getattr(self.instance, "unit", None)
        slot = attrs.get("selected_weapon_slot")
        if slot and unit and slot.unit_id != unit.id:
            raise serializers.ValidationError("Selected weapon slot must belong to the unit.")
        model_count = attrs.get("model_count", getattr(self.instance, "model_count", None))
        if unit and model_count is not None:
            model_error = validate_model_count(unit, model_count)
            if model_error:
                raise serializers.ValidationError({"model_count": model_error})
        return attrs


class ArmyListSerializer(serializers.ModelSerializer):
    units = ListUnitSerializer(many=True, read_only=True)
    total_points = serializers.SerializerMethodField()
    validation = serializers.SerializerMethodField()

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
            "validation",
        )

    def get_total_points(self, obj):
        return army_list_points(obj)

    def get_validation(self, obj):
        return army_list_validation(obj)


class AddListUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListUnit
        fields = ("unit", "model_count", "selected_weapon_slot", "notes")

    def validate_selected_weapon_slot(self, value: UnitWeaponSlot | None):
        raw_unit_id = self.initial_data.get("unit")
        try:
            unit_id = int(raw_unit_id)
        except (TypeError, ValueError):
            return value
        if value is not None and value.unit_id != unit_id:
            raise serializers.ValidationError("Selected weapon slot must belong to the unit.")
        return value

    def validate(self, attrs):
        unit = attrs.get("unit")
        model_count = attrs.get("model_count", unit.default_models if unit else 1)
        if unit:
            model_error = validate_model_count(unit, model_count)
            if model_error:
                raise serializers.ValidationError({"model_count": model_error})
        return attrs
