from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Seller, Buyer, Messages, Booking,Notification, Staff
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string


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



@receiver(post_save, sender=Booking)
def notify_on_booking(sender, instance, created, **kwargs):
    if created:
        buyer_user = instance.buyer.user
        
        # Handle vehicle purchase bookings
        if instance.booking_type == 'VEHICLE' and instance.vehicle:
            seller_user = instance.vehicle.seller.user
            
            # Create in-app notification for seller
            Notification.objects.create(
                user=seller_user,
                message=f"{buyer_user.username} booked {instance.vehicle.title}."
            )

            # Email subject & recipients
            subject = f"New Booking: {instance.vehicle.title}"
            to_email = [seller_user.email]

            # Plain text fallback
            text_message = (
                f"Hello {seller_user.username},\n\n"
                f"{buyer_user.username} has just booked your vehicle '{instance.vehicle.title}'.\n"
                f"Please log in to your Car Yard dashboard for details.\n\n"
                f"Regards,\nCar Yard Team"
            )

            html_message = render_to_string('booking_notification.html', {
                'seller': seller_user,
                'buyer': buyer_user,
                'vehicle': instance.vehicle,
            })

            email = EmailMultiAlternatives(subject, text_message, settings.DEFAULT_FROM_EMAIL, to_email)
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=True)
        
        # Handle tour bookings - notify staff/admins
        elif instance.booking_type == 'TOUR':
            # Notify all staff members about the tour booking
            staff_members = Staff.objects.all()
            # Safely format tour_date - handle both datetime objects and strings
            if instance.tour_date:
                if hasattr(instance.tour_date, 'strftime'):
                    tour_date_str = instance.tour_date.strftime('%Y-%m-%d %H:%M')
                else:
                    tour_date_str = str(instance.tour_date)
            else:
                tour_date_str = "To be confirmed"
            
            for staff in staff_members:
                Notification.objects.create(
                    user=staff.user,
                    message=f"{buyer_user.username} booked a Car Yard Tour for {tour_date_str}."
                )
            
            # Also notify superusers
            superusers = User.objects.filter(is_superuser=True)
            for admin in superusers:
                if admin not in [staff.user for staff in staff_members]:
                    Notification.objects.create(
                        user=admin,
                        message=f"{buyer_user.username} booked a Car Yard Tour for {tour_date_str}."
                    )



@receiver(post_save, sender=Messages)
def notify_on_message(sender, instance, created, **kwargs):
    if created:
        receiver_user = instance.receiver
        sender_user = instance.sender

        # In-app notification
        Notification.objects.create(
            user=receiver_user,
            message=f"New message from {sender_user.username}"
        )

        # Email details
        subject = f"New Message from {sender_user.username}"
        to_email = [receiver_user.email]

        text_message = (
            f"Hello {receiver_user.username},\n\n"
            f"You've received a new message from {sender_user.username}:\n\n"
            f"\"{instance.content}\"\n\n"
            f"Login to reply.\n\n"
            f"Car Yard Team"
        )

        
        html_message = render_to_string('message_notification.html', {
            'receiver': receiver_user,
            'sender': sender_user,
            'message': instance,
        })

        email = EmailMultiAlternatives(subject, text_message, settings.DEFAULT_FROM_EMAIL, to_email)
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=True)



@receiver(post_save, sender=User)
def create_staff_profile(sender,instance,created,**kwargs):
    if created and instance.is_staff:
     Staff.objects.get_or_create(user=instance)
