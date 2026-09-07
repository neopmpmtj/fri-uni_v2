import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Family",
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
                ("name", models.CharField(max_length=128)),
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
                "verbose_name_plural": "families",
            },
        ),
        migrations.AddConstraint(
            model_name="family",
            constraint=models.UniqueConstraint(
                Lower("name"),
                condition=models.Q(("deleted_at__isnull", True)),
                name="uniq_live_family_name_ci",
            ),
        ),
        migrations.AddConstraint(
            model_name="family",
            constraint=models.UniqueConstraint(
                fields=("is_default",),
                condition=models.Q(("deleted_at__isnull", True), ("is_default", True)),
                name="uniq_live_default_family",
            ),
        ),
        migrations.CreateModel(
            name="SubFamily",
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
                ("name", models.CharField(max_length=128)),
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
                    "family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sub_families",
                        to="proformas.family",
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
                "verbose_name": "sub-family",
                "verbose_name_plural": "sub-families",
            },
        ),
        migrations.AddConstraint(
            model_name="subfamily",
            constraint=models.UniqueConstraint(
                Lower("name"),
                "family",
                condition=models.Q(("deleted_at__isnull", True)),
                name="uniq_live_subfamily_name_ci_per_family",
            ),
        ),
        migrations.AddConstraint(
            model_name="subfamily",
            constraint=models.UniqueConstraint(
                fields=("family",),
                condition=models.Q(("deleted_at__isnull", True), ("is_default", True)),
                name="uniq_live_default_subfamily_per_family",
            ),
        ),
        migrations.AddField(
            model_name="brand",
            name="is_default",
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="brand",
            constraint=models.UniqueConstraint(
                fields=("is_default",),
                condition=models.Q(("deleted_at__isnull", True), ("is_default", True)),
                name="uniq_live_default_brand",
            ),
        ),
        migrations.CreateModel(
            name="Item",
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
                ("internal_code", models.CharField(max_length=64)),
                (
                    "kind",
                    models.CharField(
                        choices=[("indoor", "Indoor"), ("outdoor", "Outdoor")],
                        max_length=16,
                    ),
                ),
                ("btu", models.IntegerField()),
                (
                    "max_volume_m3",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                (
                    "list_price",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                ("is_default", models.BooleanField(default=False)),
                (
                    "brand",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="proformas.brand",
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
                    "sub_family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="proformas.subfamily",
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
            model_name="item",
            constraint=models.UniqueConstraint(
                Lower("internal_code"),
                condition=models.Q(("deleted_at__isnull", True)),
                name="uniq_live_item_internal_code_ci",
            ),
        ),
        migrations.AddConstraint(
            model_name="item",
            constraint=models.UniqueConstraint(
                fields=("sub_family", "brand"),
                condition=models.Q(("deleted_at__isnull", True), ("is_default", True)),
                name="uniq_live_default_item_per_subfamily_brand",
            ),
        ),
        migrations.RemoveField(
            model_name="proformaline",
            name="model",
        ),
        migrations.RemoveField(
            model_name="proformaline",
            name="style_name",
        ),
        migrations.AddField(
            model_name="proformaline",
            name="family_name",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="proformaline",
            name="sub_family_name",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="proformaline",
            name="internal_code",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="proformaline",
            name="item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="proforma_lines",
                to="proformas.item",
            ),
        ),
        migrations.DeleteModel(
            name="EquipmentModel",
        ),
        migrations.DeleteModel(
            name="Style",
        ),
    ]
