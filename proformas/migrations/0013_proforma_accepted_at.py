from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0012_contact_positions_lookup"),
    ]

    operations = [
        migrations.AddField(
            model_name="proforma",
            name="accepted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
