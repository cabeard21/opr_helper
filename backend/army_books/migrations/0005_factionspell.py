from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("army_books", "0004_native_upgrade_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="FactionSpell",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("source_uid", models.CharField(db_index=True, max_length=120)),
                ("name", models.CharField(max_length=160)),
                ("threshold", models.PositiveSmallIntegerField(default=1)),
                ("effect", models.TextField(blank=True)),
                ("spellbook_id", models.CharField(blank=True, max_length=120)),
                ("spell_type", models.IntegerField(blank=True, null=True)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "faction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="spells",
                        to="army_books.faction",
                    ),
                ),
            ],
            options={
                "ordering": ("threshold", "name", "id"),
            },
        ),
        migrations.AddConstraint(
            model_name="factionspell",
            constraint=models.UniqueConstraint(
                fields=("faction", "source_uid"),
                name="unique_faction_spell",
            ),
        ),
    ]
