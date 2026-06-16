# Caryard

Simple Django app for listing vehicles (Caryard). Supports vehicle listings, bookings, Stripe payments, WebSocket chat, and an AI chatbot.

## Quick links
- Project entry: `manage.py`  
- Settings: `cars/settings.py`  
- ASGI/WGI: `cars/asgi.py`, `cars/wsgi.py`  
- App: `caryard/` (models, views, forms, consumers, signals)  
- Templates: `caryard/templates/`  
- Static & media: `static/`, `media/`

## Project overview
Caryard is a Django-based marketplace where Buyers browse and book vehicles and Sellers list vehicles. Features:
- Vehicle listing with images
- Vehicle purchase (Stripe) and tour bookings
- Real-time chat via Django Channels + Redis
- AI chatbot (OpenAI)
- Email notifications and PDF invoices

## Project structure
- `cars/` — Django project config (settings, urls, asgi)
- `caryard/` — main app (models, views, forms, signals, consumers)
- `static/`, `media/` — assets and uploads
- `myVenv/` — (local) virtualenv

## Key models (caryard/models.py)
- Seller / Buyer (OneToOne with User, created via signals)
- Vehicle (title, description, price, image)
- Booking (VEHICLE, TOUR)
- Payment (linked to Booking)
- ChatMessage / Messages
- Notification

## All Python requirements (runtime + dev notes)

Django==4.2.7
gunicorn==21.2.0                 # Production WSGI server
Pillow==10.0.0                   # Image processing (for <ImageField>)
psycopg2-binary==2.9.7           # PostgreSQL adapter (use for production DB)
django-environ==0.10.0           # 12-factor environment variable config
python-dotenv==1.0.0             # .env file support for local development
django-crispy-forms==1.14.0      # Better form rendering
crispy-bootstrap5==0.7           # Bootstrap 5 template pack for crispy-forms
django-storages==1.15.1          # Cloud storage backends (S3, etc.)
boto3==1.28.0                    # AWS SDK (for S3 + django-storages)

# Development & testing tools
django-debug-toolbar==3.8.1
pytest==7.4.2
pytest-django==4.5.2
coverage==7.2.8

# Code quality & formatting
black==24.1.0
isort==5.12.0
flake8==6.1.0
mypy==1.10.0
pre-commit==4.6.0

# Optional: useful utilities
sqlalchemy==2.1.20               # Optional for complex DB tasks (if used)
requests==2.31.0                 # HTTP client for external API calls

Dev & testing
- django-debug-toolbar==3.8.1
- pytest==7.4.2
- pytest-django==4.5.2
- coverage==7.2.8

Code quality
- black==24.1.0
- isort==5.12.0
- flake8==6.1.0
- mypy==1.10.0
- pre-commit==4.6.0

Optional / utilities
- sqlalchemy==2.1.20
- requests==2.31.0

Recommended production/runtime extras (if using real-time features, payments, storage, PDFs)
- daphne>=4.0.0
- channels>=4.0.0
- channels-redis>=4.0.0
- stripe>=5.0.0
- reportlab>=4.0.0

## Environment variables (.env)
Required keys (examples)
- DJANGO_SECRET_KEY
- DEBUG=False
- DATABASE_URL=postgres://user:pass@host:port/dbname
- REDIS_URL=redis://host:6379/0
- AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_STORAGE_BUCKET_NAME
- STRIPE_SECRET_KEY / STRIPE_PUBLISHABLE_KEY
- OPENAI_API_KEY
- EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_PORT, EMAIL_USE_TLS

## Development (Windows)
1. Create & activate venv:
   powershell> python -m venv .venv
   powershell> .venv\Scripts\Activate.ps1
2. Install dependencies:
   powershell> pip install -r requirements.txt
3. Migrate & run:
   powershell> python manage.py migrate
   powershell> python manage.py createsuperuser
   powershell> python manage.py runserver

ASGI (WebSockets)
- Ensure Redis running on localhost:6379
- Run Daphne:
  powershell> daphne cars.asgi:application

## Testing & quality
- Run tests: `pytest` or `python manage.py test`
- Format: `black .`
- Lint: `flake8`
- Type check: `mypy`

## Production checklist
- Use PostgreSQL (DATABASE_URL), Redis (REDIS_URL)
- Serve ASGI with Daphne (WebSockets) behind Nginx, or Gunicorn for HTTP-only
- Offload static/media to S3 via `django-storages` + `boto3` (or use Whitenoise for simple deploys)
- Run `python manage.py migrate --noinput` and `collectstatic --noinput` during deploy
- Set DEBUG=False and configure secure settings (ALLOWED_HOSTS, TLS)
- Use systemd / supervisor to run daphne/gunicorn workers; use Certbot for TLS

## Important notes
- Signals in `caryard/signals.py` auto-create profiles and notifications and send emails.
- WebSocket chat route: `ws/chat/<username>/` (consumer: `caryard/consumers.py`) — room name created by alphabetically sorting participants.
- Vehicle booking flow:
  1. Vehicle bookings → Stripe checkout → payment_success view → Payment record + invoice email
  2. Tour bookings → Direct confirmation email

## Troubleshooting
- Image issues: verify MEDIA_ROOT / MEDIA_URL and uploaded files under `media/`
- WebSockets not working: check Redis, Channels config, and Daphne logs
- Stripe failures: confirm keys and webhook config

## Contributing
- Run linters/formatters and tests before PRs.
- Consider splitting dev vs prod dependencies (`requirements.txt` + `requirements-dev.txt`) for cleaner production images.

If you want, I can:
- create `requirements-prod.txt` and `requirements-dev.txt`,
- add example systemd unit files for Daphne/Gunicorn,
- or scaffold a Dockerfile and docker-compose for production.
