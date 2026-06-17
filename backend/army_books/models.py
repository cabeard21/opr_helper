from django.db import models


class Faction(models.Model):
    name = models.CharField(max_length=120)
    version = models.CharField(max_length=40)
    last_fetched = models.DateTimeField(null=True, blank=True)
    source_uid = models.CharField(max_length=120, null=True, blank=True, db_index=True)
    source_slug = models.CharField(max_length=120, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Unit(models.Model):
    faction = models.ForeignKey(
        Faction,
        on_delete=models.CASCADE,
        related_name="units",
    )
    name = models.CharField(max_length=160)
    quality = models.PositiveSmallIntegerField()
    defense = models.PositiveSmallIntegerField()
    tough = models.PositiveSmallIntegerField()
    points = models.PositiveIntegerField()
    special_rules = models.JSONField(default=dict, blank=True)
    source_uid = models.CharField(max_length=120, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Weapon(models.Model):
    name = models.CharField(max_length=160)
    range = models.PositiveSmallIntegerField()
    attacks = models.FloatField()
    attacks_string = models.CharField(max_length=40)
    ap = models.PositiveSmallIntegerField(default=0)
    special_rules = models.JSONField(default=dict, blank=True)
    source_uid = models.CharField(max_length=120, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class UnitWeaponSlot(models.Model):
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name="weapon_slots",
    )
    weapon = models.ForeignKey(
        Weapon,
        on_delete=models.CASCADE,
        related_name="unit_slots",
    )
    is_default = models.BooleanField(default=True)
    upgrade_cost = models.IntegerField(default=0)

    class Meta:
        ordering = ("unit__name", "weapon__name")

    def __str__(self):
        return f"{self.unit}: {self.weapon}"
