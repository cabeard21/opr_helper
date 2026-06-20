from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("army_books", "0004_native_upgrade_models"),
        ("lists", "0002_advisor_grouping_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ListUnitUpgrade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "list_unit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="selected_upgrades",
                        to="lists.listunit",
                    ),
                ),
                (
                    "option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="list_unit_selections",
                        to="army_books.unitupgradeoption",
                    ),
                ),
            ],
            options={
                "ordering": ("list_unit_id", "option__section__label", "option__label"),
            },
        ),
        migrations.AddConstraint(
            model_name="listunitupgrade",
            constraint=models.UniqueConstraint(
                fields=("list_unit", "option"),
                name="unique_list_unit_upgrade_option",
            ),
        ),
    ]
