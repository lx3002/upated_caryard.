from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.mail import EmailMessage, BadHeaderError
from django.template.loader import render_to_string
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import re
import json
import stripe
from django.urls import reverse

from .models import Vehicle, Seller, Buyer, Booking, Comment, Rating, Payment, ChatbotLog
from .forms import BookingForm, CommentForm, SignupForm, VehicleForm, PaymentForm

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.core.mail import EmailMessage, BadHeaderError
from django.template.loader import render_to_string
import io
from reportlab.pdfgen import canvas


stripe.api_key = ""
stripe.api_key = settings.STRIPE_SECRET_KEY



def validate_email_address(email: str) -> bool:
    """Check if email has valid format"""
    if not email:
        return False
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_regex, email))


def send_invoice_email(booking, payment):
    """Send invoice email with attached PDF invoice"""
    try:
        recipient = booking.buyer.user.email

        if not validate_email_address(recipient):
            return False, "Invalid email format."

        # ---- Generate PDF ----
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, 800, "Car Yard Invoice")
        p.setFont("Helvetica", 12)
        p.drawString(100, 770, f"Customer: {booking.buyer.user.username}")
        p.drawString(100, 750, f"Vehicle: {booking.vehicle.title}")
        p.drawString(100, 730, f"Price: ${booking.vehicle.price}")
        p.drawString(100, 710, f"Payment Method: {payment.method}")
        p.drawString(100, 690, f"Payment Date: {payment.created.strftime('%Y-%m-%d')}")
        p.drawString(100, 660, "Thank you for your purchase!")
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()

        # ---- Email Body ----
        subject = "Car Yard Payment Invoice"
        message = render_to_string("invoice_email.html", {
            "booking": booking,
            "payment": payment,
        })

        # ---- Send Email ----
        email = EmailMessage(subject, message, to=[recipient])
        email.attach("invoice.pdf", pdf, "application/pdf")
        email.send(fail_silently=False)

        return True, "Invoice sent successfully!"

    except BadHeaderError:
        return False, "Invalid email headers."
    except Exception as e:
        return False, f"Email sending failed: {str(e)}"




def home(request):
    vehicles = Vehicle.objects.all().order_by('-created')
    return render(request, 'home.html', {'vehicles': vehicles})


def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    comment_form = CommentForm()
    booking_form = BookingForm()
    return render(request, 'vehicle_detail.html', {
        'vehicle': vehicle,
        'comment_form': comment_form,
        'booking_form': booking_form,
    })


@login_required
def add_vehicle(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save(commit=False)
            seller, _ = Seller.objects.get_or_create(user=request.user)
            vehicle.seller = seller
            vehicle.save()
            return redirect('home')   # ✅ fixed
    else:
        form = VehicleForm()
    return render(request, 'add_vehicle.html', {'form': form})


@login_required
def book_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    buyer, _ = Buyer.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.vehicle = vehicle
            booking.buyer = buyer
            booking.save()

            # ✅ call helper function
            checkout_session = create_stripe_checkout_session(request, booking)

            # Save the Stripe session ID
            booking.stripe_session_id = checkout_session.id
            booking.save()

            # Redirect to Stripe Checkout
            return redirect(checkout_session.url, code=303)

    return redirect("vehicle_detail", pk=pk)


# ✅ Helper function to create Stripe session
def create_stripe_checkout_session(request, booking):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": booking.vehicle.title,
                },
                "unit_amount": int(booking.vehicle.price * 100),  # in cents
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.build_absolute_uri(
            reverse("payment_success", args=[booking.id])
        ),
        cancel_url=request.build_absolute_uri(
            reverse("payment_cancel", args=[booking.id])
        ),
    )
    return session





# ------------------- PAYMENT --------------------
@login_required
def payment_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, buyer__user=request.user)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.booking = booking
            payment.buyer = booking.buyer
            payment.amount = booking.vehicle.price
            payment.save()

            # Send invoice email with validation
            email_sent, email_message = send_invoice_email(booking, payment)
            
            if email_sent:
                messages.success(request, f"Payment successful! {email_message}")
            else:
                messages.error(request, f"Payment successful, but {email_message}")
                messages.warning(request, "Please contact support to receive your invoice.")
            
            return redirect('home')
    else:
        form = PaymentForm()

    return render(request, 'payment.html', {'form': form, 'booking': booking})



@login_required
def ajax_comment(request):
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        content = request.POST.get('content')
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
        comment = Comment.objects.create(vehicle=vehicle, user=request.user, content=content)
        return JsonResponse({
            'ok': True,
            'user': request.user.username,
            'content': comment.content,
            'created': comment.created.strftime('%Y-%m-%d %H:%M')
        })
    return JsonResponse({'ok': False}, status=400)


# ------------------- RATING --------------------
@login_required
def ajax_rate(request):
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        score = int(request.POST.get('score', 0))
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
        Rating.objects.update_or_create(
            vehicle=vehicle,
            user=request.user,
            defaults={'score': score}
        )
        return JsonResponse({'ok': True, 'average': vehicle.average_rating()})
    return JsonResponse({'ok': False}, status=400)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = "whsec_xxxxxxxxxxxxxx"   # 🔹 Replace with your Stripe webhook secret
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        try:
            booking = Booking.objects.get(stripe_session_id=session["id"])
            # Create Payment entry
            payment = Payment.objects.create(
                booking=booking,
                buyer=booking.buyer,
                amount=booking.vehicle.price,
                method="Stripe"
            )
            # Send invoice email
            send_invoice_email(booking, payment)

        except Booking.DoesNotExist:
            pass

    return HttpResponse(status=200)


def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                Buyer.objects.get_or_create(user=user)
                Seller.objects.get_or_create(user=user)
                login(request, user)
                messages.success(request, "Account created successfully! Welcome to Car Yard!")
                return redirect('home')
            except Exception as e:
                messages.error(request, f"Error creating account: {str(e)}")
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def payment_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, buyer__user=request.user)
    messages.success(request, "Payment successful! 🎉 Your booking is confirmed.")
    return redirect("home")


@login_required
def payment_cancel(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, buyer__user=request.user)
    messages.warning(request, "Payment was cancelled. You can try again.")
    return redirect("vehicle_detail", pk=booking.vehicle.id)





def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirect to next page if provided, else home
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('home')   


def search(request):
    query = request.GET.get("q", "")
    make = request.GET.get("make", "")
    price_range = request.GET.get("price", "")

    vehicles = Vehicle.objects.all()

    if query:
        vehicles = vehicles.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(seller__user__username__icontains=query)
        )

    if make:
        vehicles = vehicles.filter(title__icontains=make)

    # Filter by price
    if price_range:
        try:
            min_price, max_price = price_range.split("-")
            vehicles = vehicles.filter(price__gte=min_price, price__lte=max_price)
        except ValueError:
            pass  # ignore bad input

    return render(request, "search_results.html", {
        "vehicles": vehicles,
        "query": query,
        "make": make,
        "price_range": price_range,
    })


def chatbot_response(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "").lower()

        if "hello" in user_message or "hi" in user_message:
            bot_reply = "👋 Hello! Welcome to Car Yard. How can I assist you today?"
        elif "car" in user_message or "vehicle" in user_message:
            bot_reply = "🚗 we have many vehicles on offer at affordable rate you are free to check them out"
        elif "price" in user_message or "cost" in user_message:
            bot_reply = "💰 our vehicles vary from different ranges you can use the search functionality to filter the vehicles"
        elif "book" in user_message:
            bot_reply = "To book a vehicle, click on 'Book Now' from the vehicle card."
        elif "price" in user_message:
            bot_reply = "You can filter vehicles by price using the search feature."
        else:
            bot_reply = "I'm not sure 🤔, but I can help you explore cars, bookings, and payments."

        ChatbotLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            user_message=user_message,
            bot_reply=bot_reply
        )
        return JsonResponse({"reply":bot_reply})
    
    return JsonResponse({"error":"invalid request"}, status=400)