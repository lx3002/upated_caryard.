from django.contrib import admin
from .models import Seller, Buyer, Vehicle, Booking, Comment, Rating, Payment, ChatbotLog


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("user",)


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ("user",)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "price", "created")
    list_filter = ("seller", "created")
    search_fields = ("title", "description")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "buyer", "date")
    list_filter = ("date",)
    search_fields = ("vehicle__title", "buyer__user__username")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "user", "created", "content")
    list_filter = ("created",)
    search_fields = ("vehicle__title", "user__username", "content")


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "user", "score")
    list_filter = ("score",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("booking", "buyer", "method", "amount", "created")
    list_filter = ("method", "created")
    search_fields = ("buyer__user__username", "booking__vehicle__title")

@admin.register( ChatbotLog)
class  ChatbotLogAdmin(admin.ModelAdmin):
    list_display = ("user", "user_message", "bot_reply", "created")
    search_fields = ("user_message", "bot_reply", "user__name")
    list_filter = ("created",)
    

