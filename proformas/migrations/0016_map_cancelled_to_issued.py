from django.db import migrations


def map_cancelled_to_issued(apps, schema_editor):
    Proforma = apps.get_model("proformas", "Proforma")
    Proforma.objects.filter(status="cancelled").update(status="issued")


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0015_proforma_rejected_at"),
    ]

    operations = [
        migrations.RunPython(map_cancelled_to_issued, migrations.RunPython.noop),
    ]
