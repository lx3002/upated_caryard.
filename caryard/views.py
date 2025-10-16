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
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import re
import json
import stripe
from django.urls import reverse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.utils.timezone import localtime
import openai
from .models import Vehicle, Seller, Buyer, Booking, Comment, Rating, Payment, ChatbotLog, Messages, Notification
from .forms import BookingForm, CommentForm, SignupForm, VehicleForm, PaymentForm, MessageForm

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Messages

# Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY


# ✅ Validate email format
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
        p.drawString(50, 730, f"Vehicle: {booking.vehicle.title}")
        p.drawString(50, 710, f"Price: ${booking.vehicle.price}")
        p.drawString(50, 690, f"Payment Method: {payment.method}")
        p.drawString(50, 670, f"Payment Date: {payment.created.strftime('%Y-%m-%d %H:%M')}")
        p.drawString(50, 640, "Thank you for your purchase!")
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()

        # ---- Stylish HTML Email ----
        subject = "✅ Your Car Yard Payment Receipt"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color:#f9f9f9; padding:20px;">
            <div style="max-width:600px; margin:auto; background:white; border-radius:10px; padding:20px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
                <h2 style="text-align:center; color:#2c3e50;">🚗 Car Yard Receipt</h2>
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
                        <td style="padding:8px; font-weight:bold;">Vehicle:</td>
                        <td style="padding:8px;">{booking.vehicle.title}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Payment Method:</td>
                        <td style="padding:8px;">{payment.method}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px; font-weight:bold;">Amount Paid:</td>
                        <td style="padding:8px; color:#27ae60; font-size:16px;"><b>${booking.vehicle.price:,.2f}</b></td>
                    </tr>
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
                    Thank you for choosing <b>Car Yard</b>! 🚙
                </p>
            </div>
        </body>
        </html>
        """

        # ---- Send Email ----
        email = EmailMessage(subject, html_content, to=[recipient])
        email.content_subtype = "html"  # ✅ Make it render as HTML
        email.attach("CarYard_Invoice.pdf", pdf, "application/pdf")
        email.send(fail_silently=False)

        print(f"✅ Email sent to {recipient}")
        return True, "Invoice sent successfully!"

    except BadHeaderError:
        print("❌ Bad email header detected.")
        return False, "Invalid email headers."
    except Exception as e:
        print(f"❌ Email failed: {str(e)}")
        return False, f"Email sending failed: {str(e)}"


        # ---- Send Email ----
        email = EmailMessage(subject, message, to=[recipient])
        email.attach("invoice.pdf", pdf, "application/pdf")

        email.send(fail_silently=False)
        print(f"✅ Email sent to {recipient}")
        return True, "Invoice sent successfully!"

    except BadHeaderError:
        print("❌ Bad email header detected.")
        return False, "Invalid email headers."
    except Exception as e:
        print(f"❌ Email failed: {str(e)}")
        return False, f"Email sending failed: {str(e)}"


# ---------------- HOME ----------------
def home(request):
    vehicles = Vehicle.objects.all().order_by('-created')
    return render(request, 'home.html', {'vehicles': vehicles})


def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    booking_form = BookingForm()

    context = {
        "vehicle": vehicle,
        "booking_form": booking_form,
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


# ---------------- BOOKING ----------------
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

            # ✅ Create Stripe checkout session
            checkout_session = create_stripe_checkout_session(request, booking)

            booking.stripe_session_id = checkout_session.id
            booking.save()

            return redirect(checkout_session.url, code=303)

    return redirect("vehicle_detail", pk=pk)


# ✅ Helper: Stripe Checkout
def create_stripe_checkout_session(request, booking):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": booking.vehicle.title},
                "unit_amount": int(min(booking.vehicle.price, 999999.99) * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("payment_success", args=[booking.id])),
        cancel_url=request.build_absolute_uri(reverse("payment_cancel", args=[booking.id])),
    )
    return session


# ---------------- PAYMENT ----------------
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

            email_sent, email_message = send_invoice_email(booking, payment)

            if email_sent:
                messages.success(request, f"Payment successful! {email_message}")
            else:
                messages.error(request, f"Payment successful, but {email_message}")

            return redirect('home')
    else:
        form = PaymentForm()

    return render(request, 'payment.html', {'form': form, 'booking': booking})


@login_required
def payment_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, buyer__user=request.user)

    payment = Payment.objects.create(
        booking=booking,
        buyer=booking.buyer,
        amount=booking.vehicle.price,
        method="Stripe"
    )

    email_sent, email_message = send_invoice_email(booking, payment)

    if email_sent:
        messages.success(request, f"Payment successful! {email_message}")
    else:
        messages.error(request, f"Payment successful, but invoice failed: {email_message}")

    return redirect("home")


@login_required
def payment_cancel(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, buyer__user=request.user)
    messages.warning(request, "Payment was cancelled. You can try again.")
    return redirect("vehicle_detail", pk=booking.vehicle.id)


# ---------------- COMMENTS ----------------
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


# ---------------- RATING ----------------
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


# ---------------- STRIPE WEBHOOK ----------------
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = "whsec_xxxxxxxxxxxxxx"  # Replace with your real secret
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        try:
            booking = Booking.objects.get(stripe_session_id=session["id"])
            payment = Payment.objects.create(
                booking=booking,
                buyer=booking.buyer,
                amount=booking.vehicle.price,
                method="Stripe"
            )
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
                login(request, user)
                messages.success(request, "Account created successfully! Welcome to Car Yard!")
                return redirect('home')
            except Exception as e:
                messages.error(request, f"Error creating account: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('home')


# ---------------- SEARCH ----------------
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

    if price_range:
        try:
            min_price, max_price = price_range.split("-")
            vehicles = vehicles.filter(price__gte=min_price, price__lte=max_price)
        except ValueError:
            pass

    return render(request, "search_results.html", {
        "vehicles": vehicles,
        "query": query,
        "make": make,
        "price_range": price_range,
    })


# ---------------- CHATBOT ----------------
from openai import OpenAI
from django.http import JsonResponse
import json
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def chatbot_response(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful virtual assistant for Car Yard. Help users find cars, understand booking, prices, and dealership info."},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.6,
                max_tokens=250
            )

            reply = response.choices[0].message.content.strip()
            return JsonResponse({"reply": reply})

        except Exception as e:
            print("Chatbot error:", e)
            return JsonResponse({"reply": "Sorry, I’m having trouble responding right now. Please try again later."})






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