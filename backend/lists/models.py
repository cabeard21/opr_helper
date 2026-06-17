from django.db import models

from army_books.models import Faction, Unit, UnitWeaponSlot


class ArmyList(models.Model):
    name = models.CharField(max_length=160)
    faction = models.ForeignKey(
        Faction,
        on_delete=models.CASCADE,
        related_name="army_lists",
    )
    point_limit = models.PositiveIntegerField(default=2000)
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
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("unit__name", "id")

    def __str__(self):
        return f"{self.model_count}x {self.unit}"
