import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Lower


POWER_SEED = (
    (Decimal("9000"), "BTU"),
    (Decimal("12000"), "BTU"),
    (Decimal("18000"), "BTU"),
)


def seed_powers_and_backfill_items(apps, schema_editor):
    Power = apps.get_model("proformas", "Power")
    Item = apps.get_model("proformas", "Item")
    ProformaLine = apps.get_model("proformas", "ProformaLine")
    by_btu = {}
    for value, unit in POWER_SEED:
        row, _created = Power.objects.get_or_create(power=value, unit=unit)
        by_btu[int(value)] = row
    for item in Item.objects.all():
        power_row = by_btu.get(item.btu)
        if power_row is None:
            power_row = by_btu[9000]
        item.power_id = power_row.pk
        item.save(update_fields=["power_id"])
    for line in ProformaLine.objects.exclude(btu__isnull=True):
        line.power_value = Decimal(line.btu)
        line.power_unit = "BTU"
        line.save(update_fields=["power_value", "power_unit"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0004_subfamily_optional_brand"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Power",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("power", models.DecimalField(decimal_places=2, max_digits=12)),
                ("unit", models.CharField(max_length=32)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["power", "unit"],
            },
        ),
        migrations.AddConstraint(
            model_name="power",
            constraint=models.UniqueConstraint(
                models.F("power"),
                Lower("unit"),
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_power_unit_ci",
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="power",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items",
                to="proformas.power",
            ),
        ),
        migrations.AddField(
            model_name="proformaline",
            name="power_value",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
        migrations.AddField(
            model_name="proformaline",
            name="power_unit",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.RunPython(seed_powers_and_backfill_items, noop),
        migrations.RemoveField(
            model_name="item",
            name="btu",
        ),
        migrations.RemoveField(
            model_name="proformaline",
            name="btu",
        ),
        migrations.AlterField(
            model_name="item",
            name="power",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items",
                to="proformas.power",
            ),
        ),
    ]
