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
    min_models = models.PositiveIntegerField(default=1)
    max_models = models.PositiveIntegerField(null=True, blank=True)
    default_models = models.PositiveIntegerField(default=1)
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
    option_id = models.CharField(max_length=120, null=True, blank=True, db_index=True)
    upgrade_id = models.CharField(max_length=120, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("unit__name", "weapon__name")

    def __str__(self):
        return f"{self.unit}: {self.weapon}"


class UnitUpgradeSection(models.Model):
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name="upgrade_sections",
    )
    package_uid = models.CharField(max_length=120, blank=True)
    section_uid = models.CharField(max_length=120, db_index=True)
    label = models.CharField(max_length=240)
    variant = models.CharField(max_length=40, blank=True)
    targets = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("unit__name", "label", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("unit", "section_uid"),
                name="unique_unit_upgrade_section",
            )
        ]

    def __str__(self):
        return f"{self.unit}: {self.label}"


class UnitUpgradeOption(models.Model):
    section = models.ForeignKey(
        UnitUpgradeSection,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_uid = models.CharField(max_length=120, db_index=True)
    label = models.CharField(max_length=240)
    cost = models.IntegerField(default=0)
    gains = models.JSONField(default=list, blank=True)
    weapons = models.ManyToManyField(
        Weapon,
        through="UnitUpgradeOptionWeapon",
        related_name="upgrade_options",
        blank=True,
    )

    class Meta:
        ordering = ("section__unit__name", "section__label", "cost", "label", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("section", "option_uid"),
                name="unique_unit_upgrade_option",
            )
        ]

    def __str__(self):
        return f"{self.section}: {self.label}"


class UnitUpgradeOptionWeapon(models.Model):
    option = models.ForeignKey(
        UnitUpgradeOption,
        on_delete=models.CASCADE,
        related_name="option_weapons",
    )
    weapon = models.ForeignKey(
        Weapon,
        on_delete=models.CASCADE,
        related_name="option_weapon_links",
    )

    class Meta:
        ordering = ("option__label", "weapon__name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("option", "weapon"),
                name="unique_unit_upgrade_option_weapon",
            )
        ]

    def __str__(self):
        return f"{self.option}: {self.weapon}"
