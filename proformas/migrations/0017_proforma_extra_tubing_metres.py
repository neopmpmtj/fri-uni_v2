from decimal import Decimal

from django.db import migrations, models


def backfill_extra_tubing_metres(apps, schema_editor):
    Proforma = apps.get_model("proformas", "Proforma")
    for proforma in Proforma.objects.all().iterator():
        total = Decimal("0.00")
        lines = proforma.lines.filter(deleted_at__isnull=True).select_related(
            "tubing_length"
        )
        for line in lines:
            if not line.extra_tubing:
                continue
            if proforma.status == "issued" and line.tubing_length_value is not None:
                length = line.tubing_length_value
            elif line.tubing_length_id:
                length = line.tubing_length.length
            else:
                length = Decimal("0.00")
            total += Decimal(line.quantity) * length
        proforma.extra_tubing_metres = total
        proforma.save(update_fields=["extra_tubing_metres"])


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0016_map_cancelled_to_issued"),
    ]

    operations = [
        migrations.AddField(
            model_name="proforma",
            name="extra_tubing_metres",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True
            ),
        ),
        migrations.RunPython(backfill_extra_tubing_metres, migrations.RunPython.noop),
    ]
