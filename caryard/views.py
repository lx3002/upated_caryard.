from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.mail import EmailMessage, BadHeaderError
from django.template.loader import render_to_string
from django.db.models import Avg, Max, Min, Q, Count, Sum
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required

from django.conf import settings
import re
import json
import stripe
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
import io
import base64
import secrets
import uuid
import urllib.request
import urllib.error
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.utils.timezone import localtime, make_aware
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from openai import OpenAI
from django.http import JsonResponse
import json
from django.conf import settings
from .models import Vehicle, Seller, Buyer, Booking, Comment, Rating, Payment, ChatbotLog, Messages, Notification, Staff, ChatMessage, EmailLoginCode
from .forms import BookingForm, CommentForm, SignupForm, VehicleForm, PaymentForm, MessageForm
from .security import rate_limit

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Staff, Booking

# Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY


#  Validate email format
def validate_email_address(email: str) -> bool:
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


#  Send invoice email
def send_invoice_email(booking, payment):
    """Send formatted HTML invoice with attached PDF."""
    try:
        recipient = booking.buyer.user.email

        if not validate_email_address(recipient):
            return False, "Invalid email format."

        # ---- Generate PDF Invoice ----
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(200, 800, "Car Yard Invoice")
        p.setFont("Helvetica", 12)
        p.drawString(50, 770, f"Customer: {booking.buyer.user.username}")
        p.drawString(50, 750, f"Email: {booking.buyer.user.email}")
        if booking.vehicle:
            p.drawString(50, 730, f"Vehicle: {booking.vehicle.title}")
            p.drawString(50, 710, f"Price: ${booking.vehicle.price}")
        else:
            p.drawString(50, 730, f"Booking Type: Car Yard Tour")
            p.drawString(50, 710, f"Tour Date: {booking.tour_date.strftime('%Y-%m-%d %H:%M') if booking.tour_date else 'TBD'}")
        p.drawString(50, 690, f"Payment Method: {payment.method}")
        p.drawString(50, 670, f"Payment Date: {payment.created.strftime('%Y-%m-%d %H:%M')}")
        p.drawString(50, 640, "Thank you for your purchase!")
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()

        # ---- Stylish HTML Email ----
        subject = "Your Car Yard Payment Receipt"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color:#f9f9f9; padding:20px;">
            <div style="max-width:600px; margin:auto; background:white; border-radius:10px; padding:20px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
                <h2 style="text-align:center; color:#2c3e50;"> Car Yard Receipt</h2>
                <p style="text-align:center; color:#7f8c8d;">Thank you for your purchase! Below are your payment details.</p>

                <hr style="border:none; border-top:2px solid #3498db; width:80%; margin:20px auto;">

                <table style="width:100%; border-collapse:collapse; margin-top:20px;">
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Customer:</td>
                        <td style="padding:8px;">{booking.buyer.user.username}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Email:</td>
                        <td style="padding:8px;">{booking.buyer.user.email}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px; font-weight:bold;">{'Vehicle:' if booking.vehicle else 'Booking Type:'}</td>
                        <td style="padding:8px;">{booking.vehicle.title if booking.vehicle else 'Car Yard Tour'}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Payment Method:</td>
                        <td style="padding:8px;">{payment.method}</td>
                    </tr>
                    {f'''<tr>
                        <td style="padding:8px; font-weight:bold;">Amount Paid:</td>
                        <td style="padding:8px; color:#27ae60; font-size:16px;"><b>${booking.vehicle.price:,.2f}</b></td>
                    </tr>''' if booking.vehicle else ''}
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Date:</td>
                        <td style="padding:8px;">{payment.created.strftime('%Y-%m-%d %H:%M')}</td>
                    </tr>
                </table>

                <hr style="border:none; border-top:1px solid #ccc; margin:20px 0;">
                <p style="text-align:center; color:#7f8c8d; font-size:14px;">
                    A PDF version of your invoice is attached for your records.
                </p>

                <p style="text-align:center; color:#555;">
                    Thank you for choosing <b>Car Yard</b>! 
                </p>
            </div>
        </body>
        </html>
        """

        # ---- Send Email ----
        email = EmailMessage(subject, html_content, to=[recipient])
        email.content_subtype = "html"  #  Make it render as HTML
        email.attach("CarYard_Invoice.pdf", pdf, "application/pdf")
        email.send(fail_silently=False)

        print(f"Email sent to {recipient}")
        return True, "Invoice sent successfully!"

    except BadHeaderError:
        print(" Bad email header detected.")
        return False, "Invalid email headers."
    except Exception as e:
        print(f" Email failed: {str(e)}")
        return False, f"Email sending failed: {str(e)}"


def send_tour_booking_email(booking):
    
    try:
        recipient = booking.buyer.user.email

        if not validate_email_address(recipient):
            return False, "Invalid email format."

        tour_date_str = booking.tour_date.strftime('%Y-%m-%d %H:%M') if booking.tour_date else "To be confirmed"
        
        subject = "Car Yard Tour Booking Confirmed"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color:#f9f9f9; padding:20px;">
            <div style="max-width:600px; margin:auto; background:white; border-radius:10px; padding:20px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
                <h2 style="text-align:center; color:#2c3e50;"> Car Yard Tour Confirmation</h2>
                <p style="text-align:center; color:#7f8c8d;">Thank you for booking a tour! We're excited to show you around.</p>

                <hr style="border:none; border-top:2px solid #3498db; width:80%; margin:20px auto;">

                <table style="width:100%; border-collapse:collapse; margin-top:20px;">
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Customer:</td>
                        <td style="padding:8px;">{booking.buyer.user.username}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Email:</td>
                        <td style="padding:8px;">{booking.buyer.user.email}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Tour Date:</td>
                        <td style="padding:8px; color:#27ae60; font-size:16px;"><b>{tour_date_str}</b></td>
                    </tr>
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Booking Status:</td>
                        <td style="padding:8px;"><span style="background:#ffc107; color:#000; padding:5px 10px; border-radius:5px;">{booking.status}</span></td>
                    </tr>
                    {f'''<tr>
                        <td style="padding:8px; font-weight:bold;">Notes:</td>
                        <td style="padding:8px;">{booking.notes}</td>
                    </tr>''' if booking.notes else ''}
                </table>

                <hr style="border:none; border-top:1px solid #ccc; margin:20px 0;">
                <p style="color:#7f8c8d; font-size:14px;">
                    Our team will contact you shortly to confirm the tour details. If you have any questions, please don't hesitate to reach out.
                </p>

                <p style="text-align:center; color:#555;">
                    We look forward to seeing you at <b>Car Yard</b>! 
                </p>
            </div>
        </body>
        </html>
        """

        email = EmailMessage(subject, html_content, to=[recipient])
        email.content_subtype = "html"
        email.send(fail_silently=False)

        print(f" Tour booking email sent to {recipient}")
        return True, "Tour confirmation email sent successfully!"

    except BadHeaderError:
        print("Bad email header detected.")
        return False, "Invalid email headers."
    except Exception as e:
        print(f"Email failed: {str(e)}")
        return False, f"Email sending failed: {str(e)}"


# ---------------- HOME ----------------
def home(request):
    vehicles = Vehicle.objects.select_related('seller__user').all().order_by('-created')
    stats = {
        "vehicle_count": sum(vehicle.available_quantity for vehicle in vehicles),
        "seller_count": Seller.objects.count(),
        "booking_count": Booking.objects.count(),
        "comment_count": Comment.objects.count(),
        "average_rating": Rating.objects.aggregate(avg=Avg("score"))["avg"] or 0,
    }
    price_stats = vehicles.aggregate(min_price=Min("price"), max_price=Max("price"))
    featured_vehicles = vehicles[:3]
    return render(request, 'home.html', {
        'vehicles': vehicles,
        'stats': stats,
        'price_stats': price_stats,
        'featured_vehicles': featured_vehicles,
    })


def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    booking_form = BookingForm()
    related_vehicles = Vehicle.objects.filter(seller=vehicle.seller).exclude(pk=vehicle.pk).order_by('-created')[:3]

    context = {
        "vehicle": vehicle,
        "booking_form": booking_form,
        "related_vehicles": related_vehicles,
        "can_rate": request.user.is_authenticated and Booking.objects.filter(
            buyer__user=request.user, vehicle=vehicle, booking_type="VEHICLE",
            status="CONFIRMED", payment__status="COMPLETED",
        ).exists(),
        "user_rating": Rating.objects.filter(vehicle=vehicle, user=request.user).first()
        if request.user.is_authenticated else None,
    }
    return render(request, "vehicle_detail.html", context)

# ---------------- VEHICLE ----------------
@login_required
def add_vehicle(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save(commit=False)
            seller, _ = Seller.objects.get_or_create(user=request.user)
            vehicle.seller = seller
            vehicle.save()
            messages.success(request, "Vehicle added successfully!")
            return redirect('home')
    else:
        form = VehicleForm()
    return render(request, 'add_vehicle.html', {'form': form})


# BOOKING 
@rate_limit(10, 60, scope="booking-create", methods={"POST"})
@login_required
def book_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    buyer, _ = Buyer.objects.get_or_create(user=request.user)

    if request.method == "POST":
        booking_type = request.POST.get('booking_type', 'VEHICLE')
        tour_date_str = request.POST.get('tour_date')
        notes = request.POST.get('notes', '')
        
        
        # Parse tour_date string to datetime object if provided
        tour_date = None
        if tour_date_str:
            try:
                # Parse the datetime-local format: "YYYY-MM-DDTHH:MM"
                tour_date = datetime.strptime(tour_date_str, '%Y-%m-%dT%H:%M')
                # Make it timezone-aware
                tour_date = make_aware(tour_date)
            except (ValueError, TypeError):
                tour_date = None
        
        if booking_type in ("VEHICLE", "RENTAL") and not vehicle.is_in_stock:
            messages.error(request, "This vehicle is currently booked out.")
            return redirect("vehicle_detail", pk=pk)
        if booking_type == "RENTAL" and not vehicle.is_available_for_rent:
            messages.error(request, "This vehicle is not available for rent.")
            return redirect("vehicle_detail", pk=pk)

        rental_start = request.POST.get("rental_start") or None
        rental_end = request.POST.get("rental_end") or None
        if booking_type == "RENTAL" and (not rental_start or not rental_end or rental_end < rental_start):
            messages.error(request, "Choose a valid rental date range.")
            return redirect("vehicle_detail", pk=pk)

        with transaction.atomic():
            locked_vehicle = Vehicle.objects.select_for_update().get(pk=vehicle.pk)
            if booking_type in ("VEHICLE", "RENTAL") and not locked_vehicle.is_in_stock:
                messages.error(request, "That vehicle was just booked. Please choose another.")
                return redirect("vehicle_detail", pk=pk)
            booking = Booking.objects.create(
                booking_type=booking_type,
                vehicle=locked_vehicle if booking_type in ("VEHICLE", "RENTAL") else None,
                buyer=buyer, tour_date=tour_date, notes=notes,
                rental_start=rental_start, rental_end=rental_end,
            )

        if booking_type in ('VEHICLE', 'RENTAL'):
            return redirect("payment", booking_id=booking.id)
        else:
            # For tour booking, send confirmation email and redirect
            send_tour_booking_email(booking)
            messages.success(request, "Tour booking confirmed! Check your email for details.")
            return redirect("vehicle_detail", pk=pk)

    return redirect("vehicle_detail", pk=pk)


#  Helper: Stripe Checkout
def create_stripe_checkout_session(request, booking):
    if not booking.vehicle:
        raise ValueError("Cannot create checkout session for tour bookings")
    
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": booking.vehicle.title},
                "unit_amount": int(min(
                    booking.vehicle.daily_rental_price if booking.booking_type == "RENTAL"
                    else booking.vehicle.price, Decimal("999999.99")
                ) * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("payment_success", args=[booking.id])),
        cancel_url=request.build_absolute_uri(reverse("payment_cancel", args=[booking.id])),
        metadata={"booking_id": str(booking.id)},
        idempotency_key=f"caryard-booking-{booking.id}-stripe-v1",
    )
    return session


# ---------------- PAYMENT ----------------
@login_required
def payment_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, buyer__user=request.user)

    amount = booking.vehicle.daily_rental_price if booking.booking_type == "RENTAL" else booking.vehicle.price
    return render(request, 'payment.html', {'booking': booking, 'amount': amount})


@rate_limit(6, 60, scope="stripe-checkout")
@login_required
def stripe_checkout(request, booking_id):
    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(), id=booking_id, buyer__user=request.user
        )
        if Payment.objects.filter(booking=booking, status="COMPLETED").exists():
            messages.info(request, "This booking is already paid.")
            return redirect("my_bookings")
        try:
            checkout_session = create_stripe_checkout_session(request, booking)
        except Exception:
            messages.error(request, "Stripe checkout could not start. Check the payment configuration.")
            return redirect("payment", booking_id=booking.id)
        booking.stripe_session_id = checkout_session.id
        booking.save(update_fields=["stripe_session_id"])
    return redirect(checkout_session.url, code=303)


def _mpesa_base_url():
    return "https://sandbox.safaricom.co.ke" if settings.MPESA_ENVIRONMENT == "sandbox" else "https://api.safaricom.co.ke"


def _json_request(url, data=None, headers=None):
    payload = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=payload, headers=headers or {}, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


@rate_limit(3, 300, scope="mpesa-stk", methods={"POST"})
@login_required
def mpesa_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, buyer__user=request.user)
    if request.method != "POST":
        return redirect("payment", booking_id=booking.id)
    phone = re.sub(r"\D", "", request.POST.get("phone", ""))
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if not re.fullmatch(r"254[17]\d{8}", phone):
        messages.error(request, "Enter a valid Kenyan Safaricom number.")
        return redirect("payment", booking_id=booking.id)
    required = (settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET, settings.MPESA_PASSKEY, settings.MPESA_CALLBACK_URL)
    if not all(required):
        messages.error(request, "M-Pesa is not configured yet. Add the Daraja credentials to the environment.")
        return redirect("payment", booking_id=booking.id)
    amount = booking.vehicle.daily_rental_price if booking.booking_type == "RENTAL" else booking.vehicle.price
    with transaction.atomic():
        locked_booking = Booking.objects.select_for_update().get(pk=booking.pk)
        payment, created = Payment.objects.select_for_update().get_or_create(
            booking=locked_booking,
            defaults={
                "buyer": booking.buyer, "method": "MPESA", "amount": amount,
                "phone_number": phone, "status": "PENDING",
            },
        )
        if not created and payment.status == "COMPLETED":
            messages.info(request, "This booking has already been paid.")
            return redirect("my_bookings")
        if not created and payment.status == "PENDING" and payment.provider_request_id:
            messages.info(request, "An M-Pesa prompt is already pending for this booking.")
            return redirect("my_bookings")
        if not created:
            payment.method = "MPESA"
            payment.amount = amount
            payment.phone_number = phone
            payment.status = "PENDING"
            payment.provider_request_id = ""
            payment.idempotency_key = uuid.uuid4()
            payment.save(update_fields=[
                "method", "amount", "phone_number", "status",
                "provider_request_id", "idempotency_key",
            ])
    try:
        credentials = base64.b64encode(f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()).decode()
        token = _json_request(f"{_mpesa_base_url()}/oauth/v1/generate?grant_type=client_credentials", headers={"Authorization": f"Basic {credentials}"})["access_token"]
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()).decode()
        response = _json_request(
            f"{_mpesa_base_url()}/mpesa/stkpush/v1/processrequest",
            {
                "BusinessShortCode": settings.MPESA_SHORTCODE, "Password": password,
                "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount), "PartyA": phone, "PartyB": settings.MPESA_SHORTCODE,
                "PhoneNumber": phone, "CallBackURL": settings.MPESA_CALLBACK_URL,
                "AccountReference": f"CARYARD-{booking.id}", "TransactionDesc": "Car Yard booking",
            },
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": str(payment.idempotency_key),
            },
        )
        payment.provider_request_id = response.get("CheckoutRequestID", "")
        payment.save(update_fields=["provider_request_id"])
        messages.success(request, "M-Pesa prompt sent. Complete it on your phone.")
    except (KeyError, urllib.error.URLError, ValueError):
        messages.error(request, "M-Pesa could not start. Please try again or use Stripe.")
    return redirect("my_bookings")


@rate_limit(120, 60, scope="mpesa-callback", methods={"POST"})
@csrf_exempt
def mpesa_callback(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    try:
        callback = json.loads(request.body)["Body"]["stkCallback"]
        payment = Payment.objects.get(provider_request_id=callback["CheckoutRequestID"])
        if callback["ResultCode"] == 0:
            items = callback.get("CallbackMetadata", {}).get("Item", [])
            metadata = {item["Name"]: item.get("Value") for item in items}
            payment.status = "COMPLETED"
            payment.transaction_reference = str(metadata.get("MpesaReceiptNumber", payment.transaction_reference))
            payment.booking.status = "CONFIRMED"
            payment.booking.save(update_fields=["status"])
        else:
            payment.status = "FAILED"
        payment.save(update_fields=["status", "transaction_reference"])
    except (KeyError, ValueError, Payment.DoesNotExist):
        return JsonResponse({"ok": False}, status=400)
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


@login_required
def payment_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, buyer__user=request.user)

    # Only create payment for vehicle purchases
    if booking.booking_type == 'VEHICLE' and booking.vehicle:
        amount = booking.vehicle.daily_rental_price if booking.booking_type == "RENTAL" else booking.vehicle.price
        payment, _ = Payment.objects.update_or_create(
            booking=booking,
            defaults={"buyer": booking.buyer, "amount": amount,
                      "method": "CARD", "status": "COMPLETED"}
        )
        booking.status = "CONFIRMED"
        booking.save(update_fields=["status"])

        email_sent, email_message = send_invoice_email(booking, payment)

        if email_sent:
            messages.success(request, f"Payment successful! {email_message}")
        else:
            messages.error(request, f"Payment successful, but invoice failed: {email_message}")
    else:
        messages.success(request, "Booking confirmed successfully!")

    return redirect("home")


@login_required
def payment_cancel(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, buyer__user=request.user)
    booking.status = "CANCELLED"
    booking.save(update_fields=["status"])
    messages.warning(request, "Payment was cancelled. You can try again.")
    return redirect("vehicle_detail", pk=booking.vehicle.id)


# ---------------- COMMENTS ----------------
@rate_limit(20, 60, scope="comments", methods={"POST"})
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



@rate_limit(10, 60, scope="ratings", methods={"POST"})
@login_required
def ajax_rate(request):
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        try:
            score = int(request.POST.get('score', 0))
            service_score = int(request.POST.get('service_score', 0))
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'Invalid rating.'}, status=400)
        if score not in range(1, 6) or service_score not in range(1, 6):
            return JsonResponse({'ok': False, 'error': 'Ratings must be between 1 and 5.'}, status=400)
        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
        if not Booking.objects.filter(
            buyer__user=request.user, vehicle=vehicle, booking_type="VEHICLE",
            status="CONFIRMED", payment__status="COMPLETED",
        ).exists():
            return JsonResponse({'ok': False, 'error': 'Only verified buyers can rate this vehicle.'}, status=403)
        Rating.objects.update_or_create(
            vehicle=vehicle,
            user=request.user,
            defaults={'score': score, 'service_score': service_score,
                      'review': request.POST.get('review', '').strip()}
        )
        return JsonResponse({'ok': True, 'average': vehicle.average_rating()})
    return JsonResponse({'ok': False}, status=400)


@rate_limit(120, 60, scope="stripe-webhook", methods={"POST"})
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        try:
            booking = Booking.objects.get(stripe_session_id=session["id"])
            payment, _ = Payment.objects.update_or_create(
                booking=booking,
                defaults={
                    "buyer": booking.buyer,
                    "amount": booking.vehicle.daily_rental_price if booking.booking_type == "RENTAL" else booking.vehicle.price,
                    "method": "CARD",
                    "status": "COMPLETED",
                },
            )
            booking.status = "CONFIRMED"
            booking.save(update_fields=["status"])
            send_invoice_email(booking, payment)
        except Booking.DoesNotExist:
            pass

    return HttpResponse(status=200)


# ---------------- AUTH ----------------
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
                if _issue_login_code(request, user, reverse("home")):
                    messages.success(request, "Account created. Check your email to verify your first login.")
                    return redirect("verify_login_code")
                messages.warning(request, "Your account was created, but the verification email could not be sent. Please log in to try again.")
                return redirect("login")
            except Exception as e:
                messages.error(request, f"Error creating account: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})


@rate_limit(10, 60, scope="login", methods={"POST"})
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.email:
                messages.error(request, "Your account needs an email address before email verification can be used.")
                return render(request, 'login.html', {'form': form})
            next_url = request.GET.get('next', reverse('home'))
            if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
                next_url = reverse('home')
            # A previous session must never bypass the email challenge.
            if request.user.is_authenticated:
                logout(request)
            if _issue_login_code(request, user, next_url):
                return redirect("verify_login_code")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def _masked_email(email):
    local, domain = email.split("@", 1)
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}{'*' * max(2, len(local) - len(visible))}@{domain}"


def _issue_login_code(request, user, next_url=None):
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = EmailLoginCode.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    try:
        send_mail(
            "Your Car Yard login code",
            (
                f"Hello {user.username},\n\n"
                f"Your Car Yard verification code is: {code}\n\n"
                "It expires in 10 minutes. If you did not try to log in, you can ignore this email."
            ),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        challenge.delete()
        messages.error(request, "We could not send the verification email. Please try again shortly.")
        return False
    request.session["pending_login_code_id"] = challenge.id
    request.session["pending_login_next"] = next_url or reverse("home")
    request.session["login_code_sent_at"] = timezone.now().timestamp()
    request.session.cycle_key()
    return True


@rate_limit(10, 300, scope="login-code", methods={"POST"})
def verify_login_code(request):
    challenge_id = request.session.get("pending_login_code_id")
    challenge = EmailLoginCode.objects.select_related("user").filter(
        id=challenge_id, used=False
    ).first()
    if not challenge:
        messages.info(request, "Start a new login to receive a verification code.")
        return redirect("login")

    if challenge.is_expired:
        challenge.used = True
        challenge.save(update_fields=["used"])
        messages.error(request, "That verification code expired. Please log in again.")
        return redirect("login")

    if request.method == "POST":
        code = re.sub(r"\D", "", request.POST.get("code", ""))
        if challenge.attempts >= 5:
            challenge.used = True
            challenge.save(update_fields=["used"])
            messages.error(request, "Too many incorrect attempts. Please log in again.")
            return redirect("login")
        if len(code) == 6 and check_password(code, challenge.code_hash):
            challenge.used = True
            challenge.save(update_fields=["used"])
            login(request, challenge.user, backend="django.contrib.auth.backends.ModelBackend")
            next_url = request.session.pop("pending_login_next", reverse("home"))
            request.session.pop("pending_login_code_id", None)
            request.session.pop("login_code_sent_at", None)
            messages.success(request, "Email verified. Welcome back!")
            return redirect(next_url)
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        messages.error(request, f"Incorrect code. {max(0, 5 - challenge.attempts)} attempt(s) remaining.")

    return render(request, "verify_login_code.html", {
        "masked_email": _masked_email(challenge.user.email),
        "expires_at": challenge.expires_at,
    })


@rate_limit(5, 600, scope="login-code-resend", methods={"POST"})
def resend_login_code(request):
    if request.method != "POST":
        return redirect("verify_login_code")
    challenge = EmailLoginCode.objects.select_related("user").filter(
        id=request.session.get("pending_login_code_id"), used=False
    ).first()
    if not challenge:
        return redirect("login")
    last_sent = request.session.get("login_code_sent_at", 0)
    if timezone.now().timestamp() - last_sent < 60:
        messages.warning(request, "Please wait one minute before requesting another code.")
        return redirect("verify_login_code")
    challenge.used = True
    challenge.save(update_fields=["used"])
    if _issue_login_code(request, challenge.user, request.session.get("pending_login_next")):
        messages.success(request, "A new verification code was sent.")
    return redirect("verify_login_code")


@login_required
def logout_view(request):
    logout(request)
    return redirect('home')

def staff_signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        position = request.POST.get("position")
        phone = request.POST.get("phone")
        email = request.POST.get("email", "")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("staff_signup")

        if User.objects.filter(email=email).exists() and email:
            messages.error(request, "Email already registered.")
            return redirect("staff_signup")
        if phone and Staff.objects.filter(phone=phone).exists():
            messages.error(request, "That phone number is already registered.")
            return redirect("staff_signup")

        # Create user with staff privileges
        user = User.objects.create_user(
            username=username, 
            password=password,
            email=email if email else f"{username}@caryard.com",
        )
        user.is_staff = True  # Allow access to staff dashboard
        user.save()
        
        Staff.objects.create(user=user, position=position, phone=phone, assigned_since=timezone.now())

        messages.success(request, "Staff account created successfully! You can now log in and access your dashboard.")
        return redirect("login")

    return render(request, "staff_signup.html")


# ---------------- SEARCH ----------------
def search(request):
    query = request.GET.get("q", "").strip()
    make = request.GET.get("make", "").strip()
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")

    vehicles = Vehicle.objects.select_related('seller__user').all().order_by('-created')
    total_vehicle_count = vehicles.count()

    # Search by query (title, description, or seller)
    if query:
        vehicles = vehicles.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(seller__user__username__icontains=query)
        )

    # Filter by make/model
    if make:
        vehicles = vehicles.filter(
            Q(title__icontains=make) |
            Q(description__icontains=make)
        )

    # Filter by price range
    if min_price:
        try:
            vehicles = vehicles.filter(price__gte=Decimal(min_price))
        except (InvalidOperation, TypeError):
            pass

    if max_price:
        try:
            vehicles = vehicles.filter(price__lte=Decimal(max_price))
        except (InvalidOperation, TypeError):
            pass

    # Determine which template to use
    # If there's a search query, show results; otherwise show search form
    if query or make or min_price or max_price:
        template = "search_results.html"
    else:
        template = "search.html"

    return render(request, template, {
        "vehicles": vehicles,
        "result_count": vehicles.count(),
        "total_vehicle_count": total_vehicle_count,
        "query": query,
        "make": make,
        "min_price": min_price,
        "max_price": max_price,
    })


# ---------------- CHATBOT ----------------
from openai import OpenAI
from django.http import JsonResponse
import json
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

@rate_limit(20, 60, scope="chatbot", methods={"POST"})
def chatbot_response(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "").lower().strip()

        # Get user context
        user = request.user if request.user.is_authenticated else None
        username = user.username if user else "Guest"
        
        # Get available vehicles count
        vehicle_count = Vehicle.objects.count()
        
        # Enhanced system prompt with app-specific knowledge
        system_prompt = f"""You are a friendly and knowledgeable virtual assistant for Car Yard, an online vehicle marketplace platform. 

KEY INFORMATION ABOUT CAR YARD:
- Users can browse and search for vehicles
- Users can book vehicles and make payments via Stripe
- Sellers can add vehicles for sale
- Buyers can comment on vehicles and rate them
- There are currently {vehicle_count} vehicles available
- Payment methods include: Stripe (Credit/Debit Cards), M-Pesa, PayPal
- Users can send messages to each other
- Staff members can manage bookings and update booking statuses
- Booking statuses: PENDING, CONFIRMED, CANCELLED

USER CONTEXT:
- Current user: {username}
- User is {'authenticated' if user else 'not authenticated'}

YOUR ROLE:
- Be helpful, friendly, and concise
- Guide users on how to use the platform
- Explain features like booking, searching, adding vehicles, payments
- If asked about specific vehicles, suggest using the search feature
- If asked about booking, explain the booking process
- If asked about payments, mention the available payment methods
- Keep responses conversational and under 150 words
- Use emojis sparingly (1-2 per response max)
- If you don't know something specific, suggest contacting support or checking the website

IMPORTANT:
- Always be helpful and encouraging
- Never make up specific vehicle details or prices
- Direct users to use the search feature for finding specific vehicles
- For booking, explain they need to click "Book Now" on a vehicle detail page"""

        try:
            # Check for common queries first (fallback if API fails)
            if any(word in user_message for word in ['hello', 'hi', 'hey', 'greetings']):
                reply = f"Hello {username}!  I'm here to help you navigate Car Yard. You can ask me about booking vehicles, searching for cars, making payments, or adding your own vehicle for sale. What would you like to know?"
            elif any(word in user_message for word in ['book', 'booking', 'how to book', 'reserve']):
                reply = """To book a vehicle:
1. Browse available vehicles on the home page
2. Click "View Details" on a vehicle you like
3. Click "Book Now" button
4. Complete the booking form
5. You'll be redirected to Stripe for secure payment
6. After payment, you'll receive a confirmation email

Need help finding a specific vehicle? Use the search feature in the navigation bar! """
            elif any(word in user_message for word in ['search', 'find', 'looking for', 'vehicle']):
                reply = f"""To search for vehicles:
1. Click "Search" in the navigation bar
2. Enter keywords like make, model, or description
3. Filter by price range if needed
4. Browse the results and click "View Details" for more info

Currently, we have {vehicle_count} vehicles available. Start your search now! """
            elif any(word in user_message for word in ['payment', 'pay', 'stripe', 'card', 'money']):
                reply = """Payment options at Car Yard:
- Stripe (Credit/Debit Cards) - Secure online payment
- M-Pesa - Mobile money payment
- PayPal - Digital wallet payment

All payments are processed securely. After booking, you'll receive an invoice via email. """
            elif any(word in user_message for word in ['sell', 'add vehicle', 'list', 'post']):
                reply = """To add a vehicle for sale:
1. Click "Add Vehicle" in the navigation bar
2. Fill in the vehicle details (title, description, price)
3. Upload a clear photo of your vehicle
4. Submit the form
5. Your vehicle will appear on the home page

Make sure to include accurate information and a good photo! """
            elif any(word in user_message for word in ['help', 'support', 'assistance']):
                reply = """I'm here to help! I can assist you with:
- Booking vehicles
- Searching for cars
- Payment information
- Adding vehicles for sale
- Understanding the platform features

What specific help do you need? Just ask! """
            else:
                # Use OpenAI for other queries
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                reply = response.choices[0].message.content.strip()
            
            # Log the conversation if user is authenticated
            if user:
                try:
                    ChatbotLog.objects.create(
                        user=user,
                        user_message=user_message,
                        bot_reply=reply
                    )
                except:
                    pass  # Don't fail if logging fails
            
            return JsonResponse({"reply": reply})

        except Exception as e:
            print("Chatbot error:", e)
            # Fallback response
            fallback_replies = [
                "I'm having a bit of trouble right now. Please try asking again in a moment!",
                "Sorry, I'm experiencing some technical difficulties. Could you rephrase your question?",
                "I'm not able to process that right now. Try asking about booking, searching, or payments!"
            ]
            import random
            return JsonResponse({"reply": random.choice(fallback_replies)})






@login_required
def get_messages(request, username):
    user_to_chat = get_object_or_404(User, username=username)
    messages = Messages.objects.filter(
        Q(sender=request.user, receiver=user_to_chat) |
        Q(sender=user_to_chat, receiver=request.user)
    ).order_by('timestamp')

    data = []
    for msg in messages:
        data.append({
            "content": msg.content,
            "time": localtime(msg.timestamp).strftime("%H:%M"),
            "is_sender": msg.sender == request.user
        })

    return JsonResponse({"messages": data})









@login_required
def inbox(request):
    messages_received = Messages.objects.filter(receiver=request.user).order_by('-timestamp')
    return render(request, 'inbox.html', {'messages': messages_received})

@login_required
def send_message(request, username):
    receiver = get_object_or_404(User, username=username)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Messages.objects.create(sender=request.user, receiver=receiver, content=content)
            return redirect('inbox')
    return render(request, 'send_message.html', {'receiver': receiver})


def profile(request):
    try:
        Buyer = Buyer.objects.get(User= request.user)
        Booking = Booking.objects.filter(Buyer=Buyer).select_related('vehicle')

    except Buyer.DoesNotExist:
        Buyer = None
        Booking = None
    return render(request, 'profile.html', {
        'Buyer': Buyer, 
        'Booking': Booking
        })


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)
    notifications.update(is_read=True)
    return render(request, 'notifications.html', {'notifications': notifications})



# views.py



@login_required
def staff_dashboard(request):
    # Get staff object for logged-in user
    try:
        staff = Staff.objects.get(user=request.user)
    except Staff.DoesNotExist:
        # If user is not a staff member, redirect them
        if not request.user.is_superuser:
            messages.error(request, "You must be a staff member to access this page.")
            return redirect("home")
        staff = None

    # Superusers see all bookings; staff see only their assigned ones
    if request.user.is_superuser:
        bookings = Booking.objects.select_related('vehicle', 'buyer', 'staff').all().order_by('-date')
    elif staff:
        bookings = Booking.objects.filter(staff=staff).select_related('vehicle', 'buyer').order_by('-date')
    else:
        bookings = []

    # Calculate statistics
    total_bookings = bookings.count()
    pending_count = bookings.filter(status='PENDING').count()
    confirmed_count = bookings.filter(status='CONFIRMED').count()
    cancelled_count = bookings.filter(status='CANCELLED').count()
    tour_count = bookings.filter(booking_type='TOUR').count()
    vehicle_booking_count = bookings.filter(booking_type='VEHICLE').count()
    rental_count = bookings.filter(booking_type='RENTAL').count()
    completed_payments = Payment.objects.filter(booking__in=bookings, status="COMPLETED")
    sales_revenue = completed_payments.filter(booking__booking_type="VEHICLE").aggregate(total=Sum("amount"))["total"] or Decimal("0")
    rental_revenue = completed_payments.filter(booking__booking_type="RENTAL").aggregate(total=Sum("amount"))["total"] or Decimal("0")
    inventory = Vehicle.objects.select_related("seller__user").order_by("title")
    average_service_rating = Rating.objects.filter(service_score__gt=0).aggregate(avg=Avg("service_score"))["avg"] or 0
    chart_data = json.dumps({
        "labels": ["Sales", "Tours", "Rentals", "Cancelled"],
        "values": [vehicle_booking_count, tour_count, rental_count, cancelled_count],
    })

    return render(request, "staff_dashboard.html", {
        "staff": staff, 
        "bookings": bookings,
        "total_bookings": total_bookings,
        "pending_count": pending_count,
        "confirmed_count": confirmed_count,
        "cancelled_count": cancelled_count,
        "tour_count": tour_count,
        "vehicle_booking_count": vehicle_booking_count,
        "rental_count": rental_count,
        "sales_revenue": sales_revenue,
        "rental_revenue": rental_revenue,
        "inventory": inventory,
        "average_service_rating": average_service_rating,
        "chart_data": chart_data,
    })



@login_required
def update_booking_status(request, booking_id):
    try:
        staff = Staff.objects.get(user=request.user)
    except Staff.DoesNotExist:
        # Allow superusers to update any booking
        if not request.user.is_superuser:
            messages.error(request, "You are not authorized to perform this action.")
            return redirect("home")
        staff = None

    # Staff can only update their assigned bookings, superusers can update any
    if request.user.is_superuser:
        booking = get_object_or_404(Booking, id=booking_id)
    else:
        booking = get_object_or_404(Booking, id=booking_id, staff=staff)

    if request.method == "POST":
        new_status = request.POST.get("status")
        notes = request.POST.get("notes", "")
        
        if new_status in ["PENDING", "CONFIRMED", "CANCELLED"]:
            old_status = booking.status
            booking.status = new_status
            if notes:
                booking.notes = notes
            booking.save()

            # Create in-app notification
            booking_title = booking.vehicle.title if booking.vehicle else "Car Yard Tour"
            Notification.objects.create(
                user=booking.buyer.user,
                message=f"Your booking for {booking_title} is now {booking.status}.",
            )

            # Send email to buyer
            send_booking_status_email(booking)

            messages.success(request, f"Booking status updated from {old_status} to {new_status}. Buyer has been notified.")
            return redirect("staff_dashboard")
        else:
            messages.error(request, "Invalid status selected.")

    return render(request, "update_booking_status.html", {"booking": booking})



def send_booking_status_email(booking):
    """Send an email to the buyer when booking status changes."""
    subject = f"Your booking for {booking.vehicle.title} has been updated"
    context = {
        "buyer": booking.buyer.user.username,
        "vehicle": booking.vehicle.title,
        "status": booking.status,
        "price": booking.vehicle.price,
    }
    html_message = render_to_string("booking_status_email.html", context)
    plain_message = strip_tags(html_message)
    recipient = booking.buyer.user.email

    send_mail(
        subject,
        plain_message,
        "noreply@caryard.com",
        [recipient],
        html_message=html_message,
        fail_silently=False,
    )
@login_required
def assign_staff(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    staff_members = Staff.objects.all()

    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        selected_staff = get_object_or_404(Staff, id=staff_id)
        booking.staff = selected_staff
        booking.status = 'CONFIRMED'
        booking.save()

        messages.success(request, f"Booking for {booking.vehicle.title} assigned to {selected_staff.user.username}.")
        return redirect('staff_dashboard')  # redirect wherever you prefer

    return render(request, 'assign_staff.html', {
        'booking': booking,
        'staff_members': staff_members
    })

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def manage_bookings(request):
    """Admin/manager view to assign staff to bookings."""
    bookings = Booking.objects.select_related('vehicle', 'buyer', 'staff').all()
    staff_members = Staff.objects.all()

    if request.method == "POST":
        booking_id = request.POST.get("booking_id")
        staff_id = request.POST.get("staff_id")

        if booking_id and staff_id:
            try:
                booking = Booking.objects.get(id=booking_id)
                selected_staff = Staff.objects.get(id=staff_id)
                booking.staff = selected_staff
                booking.save()
                messages.success(request, f"{selected_staff.user.username} assigned to booking {booking.vehicle.title}.")
            except (Booking.DoesNotExist, Staff.DoesNotExist):
                messages.error(request, "Invalid booking or staff selected.")
        else:
            messages.warning(request, "Please select both booking and staff before assigning.")

        return redirect('manage_bookings')

    return render(request, "manage_bookings.html", {
        "bookings": bookings,
        "staff_members": staff_members,
        "total_bookings": bookings.count(),
        "pending_count": bookings.filter(status="PENDING").count(),
        "confirmed_count": bookings.filter(status="CONFIRMED").count(),
        "unassigned_count": bookings.filter(staff__isnull=True).count(),
    })
@login_required
def chat_with_user(request, user_id):
    """Direct chat between staff and a buyer."""
    other_user = get_object_or_404(User, id=user_id)
    messages_qs = ChatMessage.objects.filter(
        (Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user))
    ).order_by('timestamp')

    if request.method == "POST":
        message = request.POST.get('message')
        if message:
            ChatMessage.objects.create(sender=request.user, receiver=other_user, content=message)
            return redirect('chat_with_user', user_id=other_user.id)

    return render(request, 'chat_with_user.html', {
        'other_user': other_user,
        'messages': messages_qs
    })


@login_required
def my_bookings(request):
    """View for buyers to see their bookings."""
    try:
        buyer = Buyer.objects.get(user=request.user)
        bookings = Booking.objects.filter(buyer=buyer).select_related('vehicle', 'staff').order_by('-date')
    except Buyer.DoesNotExist:
        bookings = []
    
    return render(request, 'my_bookings.html', {
        'bookings': bookings
    })
