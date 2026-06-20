from rest_framework import serializers

from army_books.models import UnitUpgradeOption, UnitWeaponSlot
from lists.loadouts import effective_loadout
from lists.models import ArmyList, ListUnit, ListUnitUpgrade
from lists.validation import (
    army_list_points,
    army_list_validation,
    list_unit_points,
    validate_model_count,
    validate_parent_entry,
)


class SelectedUpgradesField(serializers.Field):
    def to_representation(self, value):
        return [selection.option_id for selection in value.all()]

    def to_internal_value(self, data):
        if data in (None, ""):
            return []
        if not isinstance(data, list):
            raise serializers.ValidationError("Selected upgrades must be a list.")
        try:
            option_ids = [int(value) for value in data]
        except (TypeError, ValueError):
            raise serializers.ValidationError("Selected upgrades must be option IDs.")
        options = list(UnitUpgradeOption.objects.filter(id__in=option_ids).select_related("section"))
        if len(options) != len(set(option_ids)):
            raise serializers.ValidationError("Selected upgrade option was not found.")
        option_lookup = {option.id: option for option in options}
        return [option_lookup[option_id] for option_id in option_ids]


class ListUnitSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    unit_points = serializers.IntegerField(source="unit.points", read_only=True)
    selected_weapon_name = serializers.CharField(
        source="selected_weapon_slot.weapon.name",
        read_only=True,
        allow_null=True,
    )
    total_points = serializers.SerializerMethodField()
    selected_upgrades = SelectedUpgradesField(required=False)
    loadout_weapon_names = serializers.SerializerMethodField()
    loadout_summary = serializers.SerializerMethodField()

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
            "selected_upgrades",
            "loadout_weapon_names",
            "loadout_summary",
            "parent_entry",
            "combined_from_count",
            "notes",
            "total_points",
        )

    def get_total_points(self, obj):
        return list_unit_points(obj)

    def get_loadout_weapon_names(self, obj):
        return effective_loadout(obj).weapon_names

    def get_loadout_summary(self, obj):
        return effective_loadout(obj).summary

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
        combined_from_count = attrs.get(
            "combined_from_count",
            getattr(self.instance, "combined_from_count", 1),
        )
        if combined_from_count < 1:
            raise serializers.ValidationError({"combined_from_count": "Combined count must be at least 1."})
        parent_entry = attrs.get("parent_entry", getattr(self.instance, "parent_entry", None))
        if self.instance is not None and "parent_entry" in attrs:
            candidate = self.instance
            candidate.parent_entry = parent_entry
            parent_error = validate_parent_entry(candidate, parent_entry)
            if parent_error:
                raise serializers.ValidationError({"parent_entry": parent_error})
        selected_upgrades = attrs.get("selected_upgrades")
        if selected_upgrades is not None and unit is not None:
            _validate_upgrade_options(unit, selected_upgrades)
        return attrs

    def update(self, instance, validated_data):
        selected_upgrades = validated_data.pop("selected_upgrades", None)
        instance = super().update(instance, validated_data)
        if selected_upgrades is not None:
            _replace_selected_upgrades(instance, selected_upgrades)
        return instance


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
            "advisor_archetype",
            "advisor_playstyle",
            "advisor_strategy_summary",
            "advisor_prompt",
            "advisor_warnings",
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
    selected_upgrades = SelectedUpgradesField(required=False)

    class Meta:
        model = ListUnit
        fields = (
            "unit",
            "model_count",
            "selected_weapon_slot",
            "selected_upgrades",
            "parent_entry",
            "combined_from_count",
            "notes",
        )

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
        combined_from_count = attrs.get("combined_from_count", 1)
        if combined_from_count < 1:
            raise serializers.ValidationError({"combined_from_count": "Combined count must be at least 1."})
        selected_upgrades = attrs.get("selected_upgrades")
        if selected_upgrades is not None and unit is not None:
            _validate_upgrade_options(unit, selected_upgrades)
        return attrs

    def create(self, validated_data):
        selected_upgrades = validated_data.pop("selected_upgrades", [])
        instance = super().create(validated_data)
        _replace_selected_upgrades(instance, selected_upgrades)
        return instance


def _validate_upgrade_options(unit, options: list[UnitUpgradeOption]) -> None:
    seen_sections: set[int] = set()
    for option in options:
        if option.section.unit_id != unit.id:
            raise serializers.ValidationError(
                {"selected_upgrades": "Selected upgrade must belong to the unit."}
            )
        if option.section_id in seen_sections:
            raise serializers.ValidationError(
                {"selected_upgrades": "Only one upgrade can be selected per section."}
            )
        seen_sections.add(option.section_id)


def _replace_selected_upgrades(instance: ListUnit, options: list[UnitUpgradeOption]) -> None:
    instance.selected_upgrades.all().delete()
    ListUnitUpgrade.objects.bulk_create(
        [ListUnitUpgrade(list_unit=instance, option=option) for option in options]
    )
