from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_company(apps, schema_editor):
    Company = apps.get_model("proformas", "Company")
    if Company.objects.exists():
        return
    Company.objects.create(
        name="Fribila",
        street="Rua da Promaça, nº4",
        postal_code="5000-081",
        city="Vila Real",
        country_code="PT",
        phone_country_id="PT",
        phone="259326314",
        phone_note="Chamada para a rede fixa nacional",
        email="info@fribila.pt",
        singleton=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0023_vat_and_validity"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Company",
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
                ("name", models.CharField(max_length=255)),
                ("tax_number", models.CharField(blank=True, max_length=9)),
                ("street", models.CharField(max_length=255)),
                ("postal_code", models.CharField(max_length=8)),
                ("city", models.CharField(max_length=128)),
                ("country_code", models.CharField(default="PT", max_length=2)),
                ("phone", models.CharField(max_length=9)),
                ("phone_note", models.CharField(blank=True, max_length=128)),
                ("email", models.EmailField(max_length=254)),
                ("contact_name", models.CharField(blank=True, max_length=255)),
                ("iban", models.CharField(blank=True, max_length=34)),
                (
                    "logo",
                    models.ImageField(
                        blank=True, null=True, upload_to="company/"
                    ),
                ),
                ("singleton", models.BooleanField(default=True, editable=False)),
                (
                    "contact_position",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="proformas.contactposition",
                    ),
                ),
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
                    "phone_country",
                    models.ForeignKey(
                        default="PT",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="proformas.country",
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
        ),
        migrations.AddConstraint(
            model_name="company",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), ("singleton", True)),
                fields=("singleton",),
                name="uniq_live_company",
            ),
        ),
        migrations.RunPython(seed_company, migrations.RunPython.noop),
    ]
