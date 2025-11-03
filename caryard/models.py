from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ---------------- SELLER MODEL ----------------
class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.user.username


# ---------------- BUYER MODEL ----------------
class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.user.username


# ---------------- VEHICLE MODEL ----------------
class Vehicle(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="vehicles")
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


# ---------------- BOOKING MODEL ----------------
class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    position = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    assigned_since = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} ({self.position or 'Staff'})"


class Booking(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
    )

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"{self.vehicle.title} booked by {self.buyer.user.username}"



# ---------------- COMMENT MODEL ----------------
class Comment(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.vehicle.title}"


# ---------------- RATING MODEL ----------------
class Rating(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.score} by {self.user.username} on {self.vehicle.title}"


# ---------------- PAYMENT MODEL ----------------
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


# ---------------- CHATBOT LOG MODEL ----------------
class ChatbotLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    user_message = models.TextField()
    bot_reply = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat by {self.user.username if self.user else 'guest'} at {self.created}"


# ---------------- MESSAGES MODEL ----------------
class Messages(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username} to {self.receiver.username}: {self.content[:30]}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}"
    



    

class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username} to {self.receiver.username}: {self.message[:30]}"


