import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
from django.db.models.functions import Lower


VAT_RATE_SEED = (
    ("VAT23", "23%", Decimal("0.2300"), True),
    ("VAT13", "13%", Decimal("0.1300"), False),
    ("VAT6", "6%", Decimal("0.0600"), False),
    ("VAT_EXEMPT", "Exempt", Decimal("0.0000"), False),
)


def seed_vat_rates_and_backfill_items(apps, schema_editor):
    VatRate = apps.get_model("proformas", "VatRate")
    Item = apps.get_model("proformas", "Item")
    vat23 = None
    for code, label, rate, is_default in VAT_RATE_SEED:
        row, _created = VatRate.objects.get_or_create(
            code=code,
            defaults={"label": label, "rate": rate, "is_default": is_default},
        )
        if code == "VAT23":
            vat23 = row
    if vat23 is not None:
        Item.objects.filter(vat_rate_id__isnull=True).update(vat_rate=vat23)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0002_catalog_items"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VatRate",
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
                ("code", models.CharField(max_length=32)),
                ("label", models.CharField(max_length=64)),
                (
                    "rate",
                    models.DecimalField(
                        decimal_places=4,
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(1),
                        ],
                    ),
                ),
                ("is_default", models.BooleanField(default=False)),
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
                "ordering": ["rate"],
            },
        ),
        migrations.AddConstraint(
            model_name="vatrate",
            constraint=models.UniqueConstraint(
                Lower("code"),
                condition=models.Q(("deleted_at__isnull", True)),
                name="uniq_live_vat_rate_code_ci",
            ),
        ),
        migrations.AddConstraint(
            model_name="vatrate",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), ("is_default", True)),
                fields=("is_default",),
                name="uniq_live_default_vat_rate",
            ),
        ),
        migrations.AddConstraint(
            model_name="vatrate",
            constraint=models.CheckConstraint(
                condition=models.Q(("rate__gte", 0), ("rate__lte", 1)),
                name="vat_rate_gte_zero_lte_one",
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="vat_rate",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items",
                to="proformas.vatrate",
            ),
        ),
        migrations.RunPython(seed_vat_rates_and_backfill_items, noop),
        migrations.AlterField(
            model_name="item",
            name="vat_rate",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items",
                to="proformas.vatrate",
            ),
        ),
    ]
