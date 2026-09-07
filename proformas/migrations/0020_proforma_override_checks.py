from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0019_seed_reference_lookups"),
    ]

    operations = [
        migrations.AddField(
            model_name="proforma",
            name="override_checks",
            field=models.BooleanField(default=False),
        ),
    ]
