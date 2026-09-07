from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proformas", "0010_client_contact_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="phone_country",
            field=models.ForeignKey(
                default="PT",
                on_delete=models.deletion.PROTECT,
                related_name="+",
                to="proformas.country",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="phone",
            field=models.CharField(max_length=9),
        ),
        migrations.AddField(
            model_name="site",
            name="email",
            field=models.EmailField(max_length=254),
        ),
        migrations.AddField(
            model_name="site",
            name="contact_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="site",
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
