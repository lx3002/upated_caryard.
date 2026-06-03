from django.contrib import admin
from .models import Seller, Buyer, Vehicle, Booking, Comment, Rating, Payment, ChatbotLog, Messages


admin.site.site_header = "Car Yard Admin"
admin.site.site_title = "Car Yard Admin"
admin.site.index_title = "Marketplace Operations"


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
    list_display = ("booking_label", "buyer", "booking_type", "status", "staff", "date")
    list_filter = ("booking_type", "status", "staff", "date")
    search_fields = ("vehicle__title", "buyer__user__username", "buyer__user__email")

    def booking_label(self, obj):
        if obj.booking_type == "TOUR":
            return "Car Yard Tour"
        return obj.vehicle.title if obj.vehicle else "Vehicle booking"

    booking_label.short_description = "Booking"


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
    
@admin.register(Messages)
class MessagesAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'content', 'timestamp')
    search_fields = ('sender__username', 'receiver__username', 'content')
    list_filter = ('timestamp',)

