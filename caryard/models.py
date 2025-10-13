from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True) 
    address = models.CharField(max_length=255, blank=True, null=True) 
    def __str__(self):
        return self.user.username


class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)  # add this
    address = models.CharField(max_length=255, blank=True, null=True)


    def __str__(self):
        return self.user.username


class Vehicle(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="vehicles/")
    created = models.DateTimeField(default=timezone.now)

    def average_rating(self):
        ratings = self.rating_set.all()
        if ratings.exists():
            return sum(r.score for r in ratings) / ratings.count()
        return 0

    def __str__(self):
        return self.title


class Booking(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.vehicle.title} booked by {self.buyer.user.username}"


class Comment(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.vehicle.title}"


class Rating(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.score} by {self.user.username} on {self.vehicle.title}"


class Payment(models.Model):
    METHOD_CHOICES = (
        ('MPESA', 'M-Pesa'),
        ('CARD', 'Credit/Debit Card'),
        ('PAYPAL', 'PayPal'),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Payment {self.amount} by {self.buyer.user.username}"
    

class  ChatbotLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_message =models.TextField()
        
    bot_reply = models.TextField()
    created = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"chat by {self.user.username if self.user else 'guest'} at {self.created}"