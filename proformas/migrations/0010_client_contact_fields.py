from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0009_country_phone_validation"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="contact_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="client",
            name="contact_position",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ceo", "CEO"),
                    ("cfo", "CFO"),
                    ("manager", "Manager"),
                    ("director", "Director"),
                    ("other", "Other"),
                ],
                max_length=16,
            ),
        ),
    ]
