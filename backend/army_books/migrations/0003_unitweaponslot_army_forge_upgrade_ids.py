from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("army_books", "0002_unit_model_counts"),
    ]

    operations = [
        migrations.AddField(
            model_name="unitweaponslot",
            name="option_id",
            field=models.CharField(blank=True, db_index=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="unitweaponslot",
            name="upgrade_id",
            field=models.CharField(blank=True, db_index=True, max_length=120, null=True),
        ),
    ]
