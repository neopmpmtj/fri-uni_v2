import re

from django.db import migrations, models


COUNTRIES = (
    ("PT", "Portugal", "351", 9),
    ("ES", "Spain", "34", 9),
    ("FR", "France", "33", 9),
    ("DE", "Germany", "49", 10),
    ("BE", "Belgium", "32", 9),
)


def seed_countries(apps, schema_editor):
    Country = apps.get_model("proformas", "Country")
    for code, name, dial_code, phone_national_digits in COUNTRIES:
        Country.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "dial_code": dial_code,
                "phone_national_digits": phone_national_digits,
            },
        )


def normalize_client_phones(apps, schema_editor):
    Client = apps.get_model("proformas", "Client")
    Country = apps.get_model("proformas", "Country")
    pt = Country.objects.get(code="PT")
    for client in Client.objects.all():
        digits = re.sub(r"\D", "", client.phone or "")
        if len(digits) >= 9:
            client.phone = digits[-9:]
        client.phone_country = pt
        client.save(update_fields=["phone", "phone_country_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0008_client_field_requirements"),
    ]

    operations = [
        migrations.CreateModel(
            name="Country",
            fields=[
                (
                    "code",
                    models.CharField(max_length=2, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=64)),
                ("dial_code", models.CharField(max_length=4)),
                ("phone_national_digits", models.PositiveSmallIntegerField()),
            ],
            options={
                "verbose_name_plural": "countries",
            },
        ),
        migrations.RunPython(seed_countries, migrations.RunPython.noop),
        migrations.AddField(
            model_name="client",
            name="phone_country",
            field=models.ForeignKey(
                default="PT",
                on_delete=models.deletion.PROTECT,
                related_name="+",
                to="proformas.country",
            ),
        ),
        migrations.RunPython(normalize_client_phones, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="client",
            name="phone",
            field=models.CharField(max_length=9),
        ),
    ]
