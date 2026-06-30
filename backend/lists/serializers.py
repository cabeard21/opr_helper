from rest_framework import serializers

from army_books.models import UnitUpgradeOption, UnitWeaponSlot
from army_books.upgrade_resolution import resolve_unit_upgrade_options
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
        selections = list(value.all())
        if not selections:
            return []
        options = [selection.option for selection in selections]
        resolution = resolve_unit_upgrade_options(selections[0].list_unit.unit, options)
        return resolution.option_ids if resolution.is_valid else [selection.option_id for selection in selections]

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


class SelectedUpgradeSelectionsField(serializers.Field):
    def to_representation(self, value):
        return [
            {"option": selection.option_id, "quantity": max(1, selection.quantity)}
            for selection in value.all()
        ]

    def to_internal_value(self, data):
        if data in (None, ""):
            return []
        if not isinstance(data, list):
            raise serializers.ValidationError("Selected upgrade selections must be a list.")
        option_ids: list[int] = []
        quantities_by_option: dict[int, int] = {}
        for item in data:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Selected upgrade selections must be objects.")
            try:
                option_id = int(item.get("option"))
                quantity = int(item.get("quantity", 1))
            except (TypeError, ValueError):
                raise serializers.ValidationError("Selected upgrade selections require option and quantity.")
            if quantity < 1:
                raise serializers.ValidationError("Selected upgrade quantity must be at least 1.")
            option_ids.append(option_id)
            quantities_by_option[option_id] = quantity
        options = list(UnitUpgradeOption.objects.filter(id__in=option_ids).select_related("section"))
        if len(options) != len(set(option_ids)):
            raise serializers.ValidationError("Selected upgrade option was not found.")
        option_lookup = {option.id: option for option in options}
        return [(option_lookup[option_id], quantities_by_option[option_id]) for option_id in option_ids]


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
    selected_upgrade_selections = SelectedUpgradeSelectionsField(
        source="selected_upgrades",
        required=False,
    )
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
            "selected_upgrade_selections",
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
            attrs["selected_upgrades"] = _validate_upgrade_options(unit, selected_upgrades)
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
    selected_upgrade_selections = SelectedUpgradeSelectionsField(
        source="selected_upgrades",
        required=False,
    )

    class Meta:
        model = ListUnit
        fields = (
            "unit",
            "model_count",
            "selected_weapon_slot",
            "selected_upgrades",
            "selected_upgrade_selections",
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
            attrs["selected_upgrades"] = _validate_upgrade_options(unit, selected_upgrades)
        return attrs

    def create(self, validated_data):
        selected_upgrades = validated_data.pop("selected_upgrades", [])
        instance = super().create(validated_data)
        _replace_selected_upgrades(instance, selected_upgrades)
        return instance


def _validate_upgrade_options(unit, options) -> list[tuple[UnitUpgradeOption, int]]:
    selections = _normalize_upgrade_selections(options)
    seen_sections: set[int] = set()
    for option, quantity in selections:
        if option.section.unit_id != unit.id:
            raise serializers.ValidationError(
                {"selected_upgrades": "Selected upgrade must belong to the unit."}
            )
        if option.section_id in seen_sections and not _is_replace_any_section(option.section):
            raise serializers.ValidationError(
                {"selected_upgrades": "Only one upgrade can be selected per section."}
            )
        seen_sections.add(option.section_id)
    replace_any_error = _replace_any_quantity_error(unit, selections)
    if replace_any_error:
        raise serializers.ValidationError({"selected_upgrades": replace_any_error})
    resolution = resolve_unit_upgrade_options(unit, [option for option, _quantity in selections])
    if not resolution.is_valid:
        raise serializers.ValidationError({"selected_upgrades": " ".join(resolution.errors)})
    quantity_by_option = {option.id: quantity for option, quantity in selections}
    return [(option, quantity_by_option.get(option.id, 1)) for option in resolution.options]


def _replace_selected_upgrades(instance: ListUnit, options) -> None:
    selections = _normalize_upgrade_selections(options)
    instance.selected_upgrades.all().delete()
    ListUnitUpgrade.objects.bulk_create(
        [
            ListUnitUpgrade(list_unit=instance, option=option, quantity=quantity)
            for option, quantity in selections
        ]
    )


def _normalize_upgrade_selections(options) -> list[tuple[UnitUpgradeOption, int]]:
    selections: list[tuple[UnitUpgradeOption, int]] = []
    for item in options or []:
        if isinstance(item, tuple):
            option, quantity = item
        else:
            option, quantity = item, 1
        selections.append((option, max(1, int(quantity))))
    return selections


def _replace_any_quantity_error(
    unit,
    selections: list[tuple[UnitUpgradeOption, int]],
) -> str | None:
    by_section: dict[int, list[tuple[UnitUpgradeOption, int]]] = {}
    for option, quantity in selections:
        by_section.setdefault(option.section_id, []).append((option, quantity))
    for section_options in by_section.values():
        section = section_options[0][0].section
        if not _is_replace_any_section(section):
            continue
        selected_quantity = sum(quantity for _option, quantity in section_options)
        available = _target_weapon_count(unit, section.targets)
        if selected_quantity > available:
            return f"{section.label} can replace at most {available} matching weapons."
    return None


def _target_weapon_count(unit, targets: list[str]) -> int:
    from army_books.upgrade_matching import weapon_matches_upgrade_target

    count = 0
    for slot in unit.weapon_slots.all():
        if slot.is_default and weapon_matches_upgrade_target(slot.weapon.name, targets):
            count += slot.count or unit.default_models or 1
    return count


def _is_replace_any_section(section) -> bool:
    affects = getattr(section, "affects", None) or {}
    return section.variant.lower() == "replace" and str(affects.get("type") or "").lower() == "any"
