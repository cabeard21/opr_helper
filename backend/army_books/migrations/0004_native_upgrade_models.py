from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("army_books", "0003_unitweaponslot_army_forge_upgrade_ids"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnitUpgradeSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("package_uid", models.CharField(blank=True, max_length=120)),
                ("section_uid", models.CharField(db_index=True, max_length=120)),
                ("label", models.CharField(max_length=240)),
                ("variant", models.CharField(blank=True, max_length=40)),
                ("targets", models.JSONField(blank=True, default=list)),
                (
                    "unit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="upgrade_sections",
                        to="army_books.unit",
                    ),
                ),
            ],
            options={
                "ordering": ("unit__name", "label", "id"),
            },
        ),
        migrations.CreateModel(
            name="UnitUpgradeOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("option_uid", models.CharField(db_index=True, max_length=120)),
                ("label", models.CharField(max_length=240)),
                ("cost", models.IntegerField(default=0)),
                ("gains", models.JSONField(blank=True, default=list)),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="options",
                        to="army_books.unitupgradesection",
                    ),
                ),
            ],
            options={
                "ordering": ("section__unit__name", "section__label", "cost", "label", "id"),
            },
        ),
        migrations.CreateModel(
            name="UnitUpgradeOptionWeapon",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="option_weapons",
                        to="army_books.unitupgradeoption",
                    ),
                ),
                (
                    "weapon",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="option_weapon_links",
                        to="army_books.weapon",
                    ),
                ),
            ],
            options={
                "ordering": ("option__label", "weapon__name", "id"),
            },
        ),
        migrations.AddField(
            model_name="unitupgradeoption",
            name="weapons",
            field=models.ManyToManyField(
                blank=True,
                related_name="upgrade_options",
                through="army_books.UnitUpgradeOptionWeapon",
                to="army_books.weapon",
            ),
        ),
        migrations.AddConstraint(
            model_name="unitupgradesection",
            constraint=models.UniqueConstraint(
                fields=("unit", "section_uid"),
                name="unique_unit_upgrade_section",
            ),
        ),
        migrations.AddConstraint(
            model_name="unitupgradeoptionweapon",
            constraint=models.UniqueConstraint(
                fields=("option", "weapon"),
                name="unique_unit_upgrade_option_weapon",
            ),
        ),
        migrations.AddConstraint(
            model_name="unitupgradeoption",
            constraint=models.UniqueConstraint(
                fields=("section", "option_uid"),
                name="unique_unit_upgrade_option",
            ),
        ),
    ]
