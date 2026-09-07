from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0013_proforma_accepted_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="proforma",
            name="replaces",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="proformas.proforma",
            ),
        ),
        migrations.AddField(
            model_name="proforma",
            name="superseded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="proformas.proforma",
            ),
        ),
    ]
