from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0005_power_ratings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="power",
            name="power",
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name="proformaline",
            name="power_value",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
