from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Seller, Buyer


@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    """Automatically create Seller and Buyer profiles when a User is created."""
    if created:
        Seller.objects.create(user=instance)
        Buyer.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profiles(sender, instance, **kwargs):
    """Save the profiles when the User is saved."""
    try:
        instance.seller.save()
    except Seller.DoesNotExist:
        pass

    try:
        instance.buyer.save()
    except Buyer.DoesNotExist:
        pass
