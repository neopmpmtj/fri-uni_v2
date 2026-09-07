import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0003_vat_rates"),
    ]

    operations = [
        migrations.AddField(
            model_name="subfamily",
            name="brand",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="owned_sub_families",
                to="proformas.brand",
            ),
        ),
    ]
