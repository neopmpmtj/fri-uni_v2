from django.db import migrations, models


def seed_validity_parameter(apps, schema_editor):
    Parameter = apps.get_model("proformas", "Parameter")
    Parameter.objects.get_or_create(
        key="default_validity_days",
        defaults={"value": "7"},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0022_financial_commercial_discounts"),
    ]

    operations = [
        migrations.AddField(
            model_name="proforma",
            name="issued_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="proforma",
            name="total_with_vat",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
        migrations.AddField(
            model_name="proforma",
            name="valid_until",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="proforma",
            name="validity_days",
            field=models.PositiveSmallIntegerField(default=7),
        ),
        migrations.AddField(
            model_name="proforma",
            name="vat_amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
        migrations.AddField(
            model_name="proformaline",
            name="vat_amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
        migrations.AddField(
            model_name="proformaline",
            name="vat_code",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="proformaline",
            name="vat_label",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="proformaline",
            name="vat_rate",
            field=models.DecimalField(
                blank=True, decimal_places=4, max_digits=5, null=True
            ),
        ),
        migrations.RunPython(seed_validity_parameter, migrations.RunPython.noop),
    ]
