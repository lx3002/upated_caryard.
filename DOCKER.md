# Car Yard with Docker

1. Copy `.env.example` to `.env` and fill in the required Django, email,
   Stripe, M-Pesa, and OpenAI values.
2. Start the application:

   ```powershell
   docker compose up --build
   ```

3. Open `http://localhost:8000`.

The `web` service runs Django through Daphne. On every container start it
applies database migrations and collects static files. Redis provides the
Channels backend and shared rate-limit cache. Named volumes preserve SQLite
data, uploaded vehicle images, collected static files, and Redis data.

To create an administrator:

```powershell
docker compose exec web python manage.py createsuperuser
```

To stop the services without deleting stored data:

```powershell
docker compose down
```
