from django.db import models

from army_books.models import Faction, Unit, UnitUpgradeOption, UnitWeaponSlot


class ArmyList(models.Model):
    name = models.CharField(max_length=160)
    faction = models.ForeignKey(
        Faction,
        on_delete=models.CASCADE,
        related_name="army_lists",
    )
    point_limit = models.PositiveIntegerField(default=2000)
    advisor_archetype = models.CharField(max_length=160, blank=True)
    advisor_playstyle = models.CharField(max_length=160, blank=True)
    advisor_strategy_summary = models.TextField(blank=True)
    advisor_prompt = models.TextField(blank=True)
    advisor_warnings = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "name")

    def __str__(self):
        return f"{self.name} ({self.point_limit} pts)"


class ListUnit(models.Model):
    army_list = models.ForeignKey(
        ArmyList,
        on_delete=models.CASCADE,
        related_name="units",
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name="list_entries",
    )
    model_count = models.PositiveIntegerField(default=1)
    selected_weapon_slot = models.ForeignKey(
        UnitWeaponSlot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="list_entries",
    )
    parent_entry = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="embedded_entries",
    )
    combined_from_count = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("unit__name", "id")

    def __str__(self):
        return f"{self.model_count}x {self.unit}"


class ListUnitUpgrade(models.Model):
    list_unit = models.ForeignKey(
        ListUnit,
        on_delete=models.CASCADE,
        related_name="selected_upgrades",
    )
    option = models.ForeignKey(
        UnitUpgradeOption,
        on_delete=models.CASCADE,
        related_name="list_unit_selections",
    )

    class Meta:
        ordering = ("list_unit_id", "option__section__label", "option__label")
        constraints = [
            models.UniqueConstraint(
                fields=("list_unit", "option"),
                name="unique_list_unit_upgrade_option",
            )
        ]

    def __str__(self):
        return f"{self.list_unit}: {self.option}"
