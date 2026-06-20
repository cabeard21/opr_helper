# Generated for advisor persistence and list-unit grouping.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lists", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="armylist",
            name="advisor_archetype",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="armylist",
            name="advisor_playstyle",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="armylist",
            name="advisor_strategy_summary",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="armylist",
            name="advisor_prompt",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="armylist",
            name="advisor_warnings",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="listunit",
            name="combined_from_count",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="listunit",
            name="parent_entry",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="embedded_entries",
                to="lists.listunit",
            ),
        ),
    ]
