from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0014_proforma_supersede_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="proforma",
            name="rejected_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="proforma",
            name="status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("issued", "Issued")],
                default="draft",
                max_length=16,
            ),
        ),
    ]
