from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lists", "0003_listunitupgrade"),
    ]

    operations = [
        migrations.AddField(
            model_name="listunitupgrade",
            name="quantity",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
