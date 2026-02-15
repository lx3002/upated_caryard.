# Generated manually for booking type support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('caryard', '0012_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='booking_type',
            field=models.CharField(choices=[('VEHICLE', 'Vehicle Purchase'), ('TOUR', 'Car Yard Tour')], default='VEHICLE', max_length=10),
        ),
        migrations.AddField(
            model_name='booking',
            name='tour_date',
            field=models.DateTimeField(blank=True, help_text='Preferred date for car yard tour', null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='notes',
            field=models.TextField(blank=True, help_text='Additional notes for the booking'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='vehicle',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, to='caryard.vehicle'),
        ),
    ]




