import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models

LEGACY_POSITIONS = (
    ("ceo", "CEO"),
    ("cfo", "CFO"),
    ("manager", "Manager"),
    ("director", "Director"),
    ("other", "Other"),
)


def seed_positions(apps, schema_editor):
    ContactPosition = apps.get_model("proformas", "ContactPosition")
    for _code, name in LEGACY_POSITIONS:
        ContactPosition.objects.get_or_create(name=name)


def migrate_position_values(apps, schema_editor):
    ContactPosition = apps.get_model("proformas", "ContactPosition")
    Client = apps.get_model("proformas", "Client")
    Site = apps.get_model("proformas", "Site")
    by_code = {
        code: ContactPosition.objects.get(name=name) for code, name in LEGACY_POSITIONS
    }
    for client in Client.objects.exclude(contact_position_old=""):
        position = by_code.get(client.contact_position_old)
        if position:
            client.contact_position = position
            client.save(update_fields=["contact_position"])
    for site in Site.objects.exclude(contact_position_old=""):
        position = by_code.get(site.contact_position_old)
        if position:
            site.contact_position = position
            site.save(update_fields=["contact_position"])


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0011_site_contact_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContactPosition",
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
                ("name", models.CharField(max_length=64)),
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
                "ordering": ["name"],
            },
        ),
        migrations.RunPython(seed_positions, migrations.RunPython.noop),
        migrations.RenameField(
            model_name="client",
            old_name="contact_position",
            new_name="contact_position_old",
        ),
        migrations.RenameField(
            model_name="site",
            old_name="contact_position",
            new_name="contact_position_old",
        ),
        migrations.AddField(
            model_name="client",
            name="contact_position",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="proformas.contactposition",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="contact_position",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="proformas.contactposition",
            ),
        ),
        migrations.RunPython(migrate_position_values, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="client",
            name="contact_position_old",
        ),
        migrations.RemoveField(
            model_name="site",
            name="contact_position_old",
        ),
        migrations.AddConstraint(
            model_name="contactposition",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("name"),
                condition=models.Q(("deleted_at__isnull", True)),
                name="uniq_live_contact_position_name_ci",
            ),
        ),
    ]
