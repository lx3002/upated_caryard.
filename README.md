# Car Yard

Car Yard is a Django vehicle marketplace where buyers can discover, compare,
book, rent, and purchase vehicles. Sellers can publish detailed listings with
multiple images, while staff manage inventory, bookings, customer communication,
and marketplace performance from an operational dashboard.

## Main features

- Vehicle marketplace with search and price filtering
- Cover, front, side, interior, and rear vehicle photographs
- Live inventory quantities and booked-out protection
- Vehicle purchases, rentals, and car-yard tour bookings
- Stripe card payments
- Safaricom M-Pesa Daraja STK Push payments
- Buyer comments and verified-purchase vehicle ratings
- Service ratings for completed purchases
- Staff assignment and booking-status management
- Sales, rental, booking, revenue, rating, and inventory statistics
- User-to-user messaging and real-time WebSocket chat
- In-app and email notifications
- AI customer-service chatbot
- Email verification codes during login and account creation
- Endpoint rate limiting backed by Redis in production
- Transaction idempotency to prevent duplicate payments
- Responsive user interface

## Technology

- Python 3.10
- Django 5.2
- Django Channels and Daphne
- Redis and `channels-redis`
- SQLite
- Stripe
- Safaricom Daraja
- OpenAI API
- ReportLab
- Bootstrap and Font Awesome

## Project structure

```text
cars/                 Django project settings, URLs, ASGI and WSGI
caryard/              Main marketplace application
  migrations/         Database schema history
  templates/          Django HTML templates
  models.py           Marketplace data models
  views.py            Authentication, booking, payment and UI logic
  consumers.py        WebSocket chat consumer
  security.py         Shared endpoint rate limiter
static/               Source styles, scripts and images
media/                Uploaded vehicle photographs
docker/               Container startup scripts
Dockerfile            Django application container
docker-compose.yml    Django and Redis development stack
manage.py             Django command-line entry point
```

## User roles

### Buyers

Buyers can browse the inventory, schedule tours, purchase or rent available
vehicles, complete payments, communicate with sellers, and review vehicles they
have successfully purchased.

### Sellers

A seller profile is created automatically with each customer account. Sellers
can publish vehicles, set inventory quantities, enable rentals, define daily
rental prices, and upload multiple vehicle views.

### Staff

Staff members manage assigned bookings, update their status, contact buyers,
and monitor operational statistics.

### Administrators

Superusers can access every booking, assign staff, manage marketplace records,
inspect inventory and payment state, and use the Django administration panel.

## Local installation

### 1. Create or activate a virtual environment

The repository currently includes a Windows virtual environment:

```powershell
.\myVenv\Scripts\Activate.ps1
```

For a clean installation:

```powershell
python -m venv myVenv
.\myVenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure the environment

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Fill in the credentials needed for the features you plan to use. Never commit
the completed `.env` file.

### 3. Apply database migrations

```powershell
python manage.py migrate
```

### 4. Create an administrator

```powershell
python manage.py createsuperuser
```

### 5. Start Redis

Redis is required for shared rate limits and WebSocket chat. It should be
available at the value configured in `REDIS_URL`.

### 6. Run the application

For normal Django development:

```powershell
python manage.py runserver
```

For WebSocket support:

```powershell
daphne -b 127.0.0.1 -p 8000 cars.asgi:application
```

Open `http://127.0.0.1:8000`.

## Docker

Docker runs the Django ASGI server and Redis together:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The container automatically applies migrations and collects static files before
starting Daphne. Named volumes preserve the SQLite database, uploaded media,
collected static files, and Redis data.

Create an administrator inside Docker:

```powershell
docker compose exec web python manage.py createsuperuser
```

Stop the stack without deleting stored data:

```powershell
docker compose down
```

More Docker details are available in [DOCKER.md](DOCKER.md).

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Cryptographic signing key |
| `DJANGO_DEBUG` | Enables or disables debug mode |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `SITE_URL` | Public base URL |
| `DB_PATH` | Optional SQLite database location |
| `REDIS_URL` | Channels and shared rate-limit Redis connection |
| `EMAIL_HOST_USER` | SMTP sender account |
| `EMAIL_HOST_PASSWORD` | SMTP account or application password |
| `STRIPE_SECRET_KEY` | Stripe server key |
| `STRIPE_PUBLISHABLE_KEY` | Stripe browser key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signature secret |
| `MPESA_ENVIRONMENT` | `sandbox` or production |
| `MPESA_CONSUMER_KEY` | Daraja consumer key |
| `MPESA_CONSUMER_SECRET` | Daraja consumer secret |
| `MPESA_SHORTCODE` | M-Pesa business shortcode |
| `MPESA_PASSKEY` | Daraja STK Push passkey |
| `MPESA_CALLBACK_URL` | Public HTTPS Daraja callback |
| `OPENAI_API_KEY` | AI chatbot access |

See [.env.example](.env.example) for a ready-to-copy template.

## Authentication

Passwords do not immediately create a browser session. After valid credentials
are submitted, Car Yard sends a six-digit verification code to the account
email address.

- Codes expire after 10 minutes.
- Five incorrect attempts invalidate a challenge.
- Resending is limited to once per minute.
- Codes are stored as secure hashes.
- Existing sessions cannot bypass a new verification challenge.
- Account creation also requires verification before the first login.

SMTP credentials must be valid for codes to arrive. Gmail accounts should use
an application password rather than the normal account password.

## Inventory and booking rules

Each vehicle has a total quantity. Its available quantity is calculated by
subtracting active purchase and rental bookings. Database locking is used while
creating bookings so two simultaneous customers cannot reserve the final unit.

Cancelled bookings release their reservation. Booked-out vehicles remain
visible but cannot be booked again until inventory becomes available.

## Payments and idempotency

### Stripe

Stripe Checkout uses a stable idempotency key derived from the booking. Repeated
requests for the same booking therefore cannot create multiple independent
checkout operations. Stripe webhook signatures are validated using
`STRIPE_WEBHOOK_SECRET`.

Stripe webhook endpoint:

```text
/payment/stripe/webhook/
```

### M-Pesa

The M-Pesa flow validates and normalizes Kenyan telephone numbers before
starting an STK Push. Every payment stores:

- An application idempotency key
- The Daraja checkout request ID
- The final M-Pesa receipt number
- Current payment status

If a prompt is already pending, repeated submissions do not send another one.
Completed bookings cannot be charged again.

Daraja callback endpoint:

```text
/payment/mpesa/callback/
```

The callback URL must be publicly reachable over HTTPS.

## Rate limiting

Sensitive or expensive endpoints are protected by request limits, including:

- Password login
- Email-code verification and resending
- Booking creation
- Stripe checkout
- M-Pesa STK Push
- Stripe and M-Pesa callbacks
- Comments and ratings
- AI chatbot requests

Limited requests receive HTTP status `429` and a `Retry-After` header. Logged-in
limits use the user ID; anonymous limits use the remote address. Docker uses
Redis so limits are shared across application processes.

## WebSocket chat

The WebSocket route is:

```text
ws/chat/<username>/
```

Both participants join the same room because usernames are sorted when the room
name is generated. Redis must be available for channel messaging.

## Email and PDF receipts

Successful payments can send an HTML receipt with a generated PDF invoice.
Booking and message signals also create in-app notifications and may send email
notifications.

## Tests

Run the complete test suite:

```powershell
python manage.py test caryard --noinput
```

Run only authentication tests:

```powershell
python manage.py test caryard.tests.AuthViewTest --noinput
```

Check configuration and pending model changes:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Useful management commands

```powershell
# Create new migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Load included sample data
python manage.py loaddata caryard/fixtures/testdata.json

# Collect production static assets
python manage.py collectstatic --noinput

# Open the Django shell
python manage.py shell
```

## Production checklist

- Set `DJANGO_DEBUG=False`.
- Replace the development `DJANGO_SECRET_KEY`.
- Restrict `DJANGO_ALLOWED_HOSTS`.
- Use HTTPS.
- Configure a persistent database and backups.
- Run Redis as a private authenticated service.
- Configure valid SMTP credentials.
- Register the Stripe webhook and Daraja callback.
- Protect API keys and rotate exposed credentials.
- Serve collected static files and uploaded media appropriately.
- Monitor failed logins, HTTP `429` responses, payment callbacks, and email
  delivery failures.

## License

No license has been specified. Add a license file before distributing or
publishing the project for third-party use.
