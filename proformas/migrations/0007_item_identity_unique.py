from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0006_power_integer"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="item",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("sub_family", "brand", "kind", "power"),
                name="uniq_live_item_identity",
            ),
        ),
    ]
