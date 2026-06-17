from rest_framework import serializers

from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon


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
        fields = ("id", "weapon", "is_default", "upgrade_cost")


class UnitSerializer(serializers.ModelSerializer):
    weapon_slots = UnitWeaponSlotSerializer(many=True, read_only=True)

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
            "special_rules",
            "source_uid",
            "weapon_slots",
        )
