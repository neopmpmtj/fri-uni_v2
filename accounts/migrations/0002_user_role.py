from django.db import migrations, models


def set_superuser_role(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_superuser=True).update(role="admin", is_staff=True)
    User.objects.filter(is_superuser=False).update(is_staff=False)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("staff", "Staff"), ("admin", "Admin")],
                default="staff",
                max_length=16,
            ),
        ),
        migrations.RunPython(set_superuser_role, migrations.RunPython.noop),
    ]
