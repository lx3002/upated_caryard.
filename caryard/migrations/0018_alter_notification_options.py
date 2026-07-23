from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("caryard", "0017_emaillogincode")]

    operations = [
        migrations.AlterModelOptions(
            name="notification",
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
