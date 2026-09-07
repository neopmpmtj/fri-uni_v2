from decimal import Decimal

from django.db import migrations


PARAMETER_SEED = (
    ("currency", "EUR"),
    ("default_upfront_discount_percent", "10"),
    ("tubing_length_unit", "m"),
)

BRAND_SEED = ("Mitsubishi", "LG", "Nippon", "Daikin")

TUBING_SEED = (
    (Decimal("3.00"), Decimal("25.00")),
    (Decimal("5.00"), Decimal("40.00")),
    (Decimal("10.00"), Decimal("70.00")),
)


def seed_reference_lookups(apps, schema_editor):
    Parameter = apps.get_model("proformas", "Parameter")
    Family = apps.get_model("proformas", "Family")
    Brand = apps.get_model("proformas", "Brand")
    TubingLength = apps.get_model("proformas", "TubingLength")

    for key, value in PARAMETER_SEED:
        Parameter.objects.get_or_create(key=key, defaults={"value": value})

    Family.objects.get_or_create(
        name="Air conditioners",
        defaults={"is_default": True},
    )

    for name in BRAND_SEED:
        Brand.objects.get_or_create(name=name)

    for length, price in TUBING_SEED:
        TubingLength.objects.get_or_create(
            length=length,
            defaults={"price": price},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0018_ac_pairing"),
    ]

    operations = [
        migrations.RunPython(seed_reference_lookups, migrations.RunPython.noop),
    ]
