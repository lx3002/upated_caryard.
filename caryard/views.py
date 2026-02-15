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
from django.contrib.admin.views.decorators import staff_member_required

from django.conf import settings
import re
import json
import stripe
from django.urls import reverse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.utils.timezone import localtime, make_aware
from datetime import datetime
from openai import OpenAI
from django.http import JsonResponse
import json
from django.conf import settings
from .models import Vehicle, Seller, Buyer, Booking, Comment, Rating, Payment, ChatbotLog, Messages, Notification, Staff,ChatMessage
from .forms import BookingForm, CommentForm, SignupForm, VehicleForm, PaymentForm, MessageForm

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


def send_tour_booking_email(booking):
    """Send confirmation email for car yard tour booking."""
    try:
        recipient = booking.buyer.user.email

        if not validate_email_address(recipient):
            return False, "Invalid email format."

        tour_date_str = booking.tour_date.strftime('%Y-%m-%d %H:%M') if booking.tour_date else "To be confirmed"
        
        subject = "✅ Car Yard Tour Booking Confirmed"
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

        print(f"✅ Tour booking email sent to {recipient}")
        return True, "Tour confirmation email sent successfully!"

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
        
        # Create booking
        booking = Booking.objects.create(
            booking_type=booking_type,
            vehicle=vehicle if booking_type == 'VEHICLE' else None,
            buyer=buyer,
            tour_date=tour_date,
            notes=notes
        )

        if booking_type == 'VEHICLE':
            # For vehicle purchase, redirect to Stripe payment
            checkout_session = create_stripe_checkout_session(request, booking)
            booking.stripe_session_id = checkout_session.id
            booking.save()
            return redirect(checkout_session.url, code=303)
        else:
            # For tour booking, send confirmation email and redirect
            send_tour_booking_email(booking)
            messages.success(request, "Tour booking confirmed! Check your email for details.")
            return redirect("vehicle_detail", pk=pk)

    return redirect("vehicle_detail", pk=pk)


# ✅ Helper: Stripe Checkout
def create_stripe_checkout_session(request, booking):
    if not booking.vehicle:
        raise ValueError("Cannot create checkout session for tour bookings")
    
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

    # Only create payment for vehicle purchases
    if booking.booking_type == 'VEHICLE' and booking.vehicle:
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
    else:
        messages.success(request, "Booking confirmed successfully!")

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

        # Create user with staff privileges
        user = User.objects.create_user(
            username=username, 
            password=password,
            email=email if email else f"{username}@caryard.com"
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

    vehicles = Vehicle.objects.all().order_by('-created')

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
            vehicles = vehicles.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            pass

    if max_price:
        try:
            vehicles = vehicles.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            pass

    # Determine which template to use
    # If there's a search query, show results; otherwise show search form
    if query or make or min_price or max_price:
        template = "search_results.html"
    else:
        template = "search.html"

    return render(request, template, {
        "vehicles": vehicles,
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
                reply = f"Hello {username}! 👋 I'm here to help you navigate Car Yard. You can ask me about booking vehicles, searching for cars, making payments, or adding your own vehicle for sale. What would you like to know?"
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
    tour_count = bookings.filter(booking_type='TOUR').count()

    return render(request, "staff_dashboard.html", {
        "staff": staff, 
        "bookings": bookings,
        "total_bookings": total_bookings,
        "pending_count": pending_count,
        "confirmed_count": confirmed_count,
        "tour_count": tour_count,
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
                messages.success(request, f"✅ {selected_staff.user.username} assigned to booking {booking.vehicle.title}.")
            except (Booking.DoesNotExist, Staff.DoesNotExist):
                messages.error(request, "❌ Invalid booking or staff selected.")
        else:
            messages.warning(request, "Please select both booking and staff before assigning.")

        return redirect('manage_bookings')

    return render(request, "manage_bookings.html", {
        "bookings": bookings,
        "staff_members": staff_members
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