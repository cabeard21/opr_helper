from rest_framework import serializers

from army_books.models import (
    Faction,
    Unit,
    UnitUpgradeOption,
    UnitUpgradeSection,
    UnitWeaponSlot,
    Weapon,
)
from lists.validation import effective_max_models


class FactionSerializer(serializers.ModelSerializer):
    unit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Faction
        fields = ("id", "name", "version", "last_fetched", "source_uid", "unit_count")


class WeaponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Weapon
        fields = (
            "id",
            "name",
            "range",
            "attacks",
            "attacks_string",
            "ap",
            "special_rules",
            "source_uid",
        )


class UnitWeaponSlotSerializer(serializers.ModelSerializer):
    weapon = WeaponSerializer(read_only=True)

    class Meta:
        model = UnitWeaponSlot
        fields = ("id", "weapon", "is_default", "count", "upgrade_cost", "option_id", "upgrade_id")


class UnitUpgradeOptionSerializer(serializers.ModelSerializer):
    weapons = WeaponSerializer(many=True, read_only=True)

    class Meta:
        model = UnitUpgradeOption
        fields = ("id", "option_uid", "label", "cost", "gains", "weapons")


class UnitUpgradeSectionSerializer(serializers.ModelSerializer):
    options = UnitUpgradeOptionSerializer(many=True, read_only=True)

    class Meta:
        model = UnitUpgradeSection
        fields = ("id", "package_uid", "section_uid", "label", "variant", "targets", "affects", "options")


class UnitSerializer(serializers.ModelSerializer):
    weapon_slots = UnitWeaponSlotSerializer(many=True, read_only=True)
    upgrade_sections = UnitUpgradeSectionSerializer(many=True, read_only=True)
    max_models = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = (
            "id",
            "faction",
            "name",
            "quality",
            "defense",
            "tough",
            "points",
            "min_models",
            "max_models",
            "default_models",
            "special_rules",
            "source_uid",
            "weapon_slots",
            "upgrade_sections",
        )

    def get_max_models(self, obj):
        return effective_max_models(obj)
