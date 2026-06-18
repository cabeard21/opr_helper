from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("army_books", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="unit",
            name="default_models",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="unit",
            name="max_models",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="unit",
            name="min_models",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
