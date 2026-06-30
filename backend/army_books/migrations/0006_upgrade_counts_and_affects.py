from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("army_books", "0005_factionspell"),
    ]

    operations = [
        migrations.AddField(
            model_name="unitweaponslot",
            name="count",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="unitupgradesection",
            name="affects",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="unitupgradeoptionweapon",
            name="count",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
