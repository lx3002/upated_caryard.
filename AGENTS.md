# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview
Car Yard is a Django-based vehicle marketplace where users can browse, book, and purchase vehicles. The platform supports vehicle purchases with Stripe payments, car yard tour bookings, real-time chat via WebSockets, and an AI-powered chatbot.

## Architecture

### Project Structure
- `cars/` - Django project configuration (settings, urls, asgi)
- `caryard/` - Main Django application containing all business logic
- `static/` - Frontend assets (Bootstrap, jQuery, custom CSS/JS)
- `media/` - User-uploaded content (vehicle images)
- `myVenv/` - Python virtual environment

### User Roles
- **Buyer** - Can browse vehicles, make bookings, process payments, leave comments/ratings
- **Seller** - Can list vehicles for sale (created automatically with Buyer on signup)
- **Staff** - Can manage bookings, update booking statuses, access staff dashboard
- **Superuser** - Full admin access to all bookings and management features

### Key Models (`caryard/models.py`)
- `Seller`/`Buyer` - OneToOne with Django User, created via signals on user registration
- `Vehicle` - Listed by Sellers, contains title, description, price, image
- `Booking` - Two types: VEHICLE (purchase) and TOUR (car yard visit)
- `Payment` - Linked to Booking, supports Stripe/M-Pesa/PayPal
- `Staff` - Staff member profiles with position and assigned bookings
- `ChatMessage`/`Messages` - User-to-user messaging
- `Notification` - In-app notifications triggered by signals

### External Integrations
- **Stripe** - Payment processing for vehicle purchases
- **OpenAI** - GPT-4o-mini powers the customer service chatbot
- **Django Channels + Redis** - Real-time WebSocket chat
- **SMTP (Gmail)** - Email notifications and invoice delivery with PDF attachments

## Development Commands

### Activate virtual environment
```powershell
.\myVenv\Scripts\Activate.ps1
```

### Run development server
```powershell
python manage.py runserver
```

### Run with ASGI (for WebSocket support)
Requires Redis running on localhost:6379
```powershell
daphne cars.asgi:application
```

### Database migrations
```powershell
python manage.py makemigrations
python manage.py migrate
```

### Create superuser
```powershell
python manage.py createsuperuser
```

### Load test fixtures
```powershell
python manage.py loaddata caryard/fixtures/testdata.json
```

### Collect static files
```powershell
python manage.py collectstatic
```

## Key Dependencies
- Django 5.2.6
- channels / channels-redis (WebSockets)
- stripe (payments)
- openai (chatbot)
- python-dotenv (environment variables)
- django-widget-tweaks (form styling)
- reportlab (PDF invoice generation)
- Pillow (image handling)

## Environment Variables (`.env`)
Required keys:
- `OPENAI_API_KEY` - For chatbot functionality
- `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` - Payment processing

Email is currently hardcoded in `cars/settings.py` - consider moving to `.env`.

## Important Notes

### Signals (`caryard/signals.py`)
- Auto-creates Buyer/Seller profiles on User creation
- Sends email notifications on new bookings and messages
- Creates in-app Notification records

### WebSocket Chat
- Route: `ws/chat/<username>/`
- Consumer: `caryard/consumers.py`
- Creates room names alphabetically sorted to ensure both users join same room

### Booking Flow
1. Vehicle bookings → Stripe checkout → payment_success view → Payment record + email invoice
2. Tour bookings → Direct confirmation email, no payment required

### Admin Panel
Access at `/admin/` - models registered in `caryard/admin.py` with custom list displays and filters.
