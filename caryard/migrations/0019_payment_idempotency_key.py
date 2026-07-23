from django.db import migrations, models
import uuid


def add_unique_payment_keys(apps, schema_editor):
    Payment = apps.get_model("caryard", "Payment")
    for payment in Payment.objects.all().iterator():
        payment.idempotency_key = uuid.uuid4()
        payment.save(update_fields=["idempotency_key"])


class Migration(migrations.Migration):
    dependencies = [("caryard", "0018_alter_notification_options")]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="provider_request_id",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name="payment",
            name="idempotency_key",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(add_unique_payment_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="payment",
            name="idempotency_key",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
