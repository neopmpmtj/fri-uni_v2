from django.db import migrations, models


def rename_discount_parameters(apps, schema_editor):
    Parameter = apps.get_model("proformas", "Parameter")
    Parameter.objects.filter(key="default_upfront_discount_percent").update(
        key="default_financial_discount_percent"
    )
    Parameter.objects.get_or_create(
        key="default_commercial_discount_percent",
        defaults={"value": "0"},
    )
    Proforma = apps.get_model("proformas", "Proforma")
    Proforma.objects.filter(commercial_discount_amount__isnull=True).update(
        commercial_discount_amount=0
    )


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0021_power_volume_default_indoor"),
    ]

    operations = [
        migrations.RenameField(
            model_name="proforma",
            old_name="upfront_discount_percent",
            new_name="financial_discount_percent",
        ),
        migrations.RenameField(
            model_name="proforma",
            old_name="discount_amount",
            new_name="financial_discount_amount",
        ),
        migrations.AddField(
            model_name="proforma",
            name="commercial_discount_percent",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=5
            ),
        ),
        migrations.AddField(
            model_name="proforma",
            name="commercial_discount_amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
        migrations.RunPython(rename_discount_parameters, migrations.RunPython.noop),
    ]
