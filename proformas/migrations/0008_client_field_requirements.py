from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0007_item_identity_unique"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="client",
            name="uniq_live_client_tax_number",
        ),
        migrations.AlterField(
            model_name="client",
            name="city",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AlterField(
            model_name="client",
            name="email",
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name="client",
            name="phone",
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name="client",
            name="postal_code",
            field=models.CharField(blank=True, max_length=8),
        ),
        migrations.AlterField(
            model_name="client",
            name="street",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="client",
            name="tax_number",
            field=models.CharField(blank=True, max_length=9),
        ),
        migrations.AddConstraint(
            model_name="client",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("deleted_at__isnull", True),
                    models.Q(("tax_number", ""), _negated=True),
                ),
                fields=("tax_number",),
                name="uniq_live_client_tax_number",
            ),
        ),
    ]
