from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [("caryard", "0015_alter_staff_position_alter_vehicle_price_and_more")]

    operations = [
        migrations.AddField(model_name="vehicle", name="front_image", field=models.ImageField(blank=True, null=True, upload_to="vehicles/")),
        migrations.AddField(model_name="vehicle", name="side_image", field=models.ImageField(blank=True, null=True, upload_to="vehicles/")),
        migrations.AddField(model_name="vehicle", name="interior_image", field=models.ImageField(blank=True, null=True, upload_to="vehicles/")),
        migrations.AddField(model_name="vehicle", name="rear_image", field=models.ImageField(blank=True, null=True, upload_to="vehicles/")),
        migrations.AddField(model_name="vehicle", name="quantity", field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name="vehicle", name="is_available_for_rent", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="vehicle", name="daily_rental_price", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="booking", name="rental_start", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="booking", name="rental_end", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="booking", name="stripe_session_id", field=models.CharField(blank=True, max_length=255, null=True, unique=True)),
        migrations.AlterField(model_name="booking", name="booking_type", field=models.CharField(choices=[("VEHICLE", "Vehicle Purchase"), ("RENTAL", "Vehicle Rental"), ("TOUR", "Car Yard Tour")], default="VEHICLE", max_length=10)),
        migrations.AddField(model_name="rating", name="service_score", field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
        migrations.AddField(model_name="rating", name="review", field=models.TextField(blank=True)),
        migrations.AddField(model_name="rating", name="created", field=models.DateTimeField(auto_now_add=True)),
        migrations.AlterField(model_name="rating", name="score", field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
        migrations.AddConstraint(model_name="rating", constraint=models.UniqueConstraint(fields=("vehicle", "user"), name="unique_vehicle_rating")),
        migrations.AddField(model_name="payment", name="status", field=models.CharField(default="PENDING", max_length=20)),
        migrations.AddField(model_name="payment", name="transaction_reference", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="payment", name="phone_number", field=models.CharField(blank=True, max_length=20)),
    ]
