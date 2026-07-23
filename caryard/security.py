import hashlib
from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse, HttpResponse


def _client_identity(request):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"


def rate_limit(limit, window, scope=None, methods=None):
    
    allowed_methods = {method.upper() for method in methods} if methods else None

    def decorator(view):
        limiter_scope = scope or f"{view.__module__}.{view.__name__}"

        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if allowed_methods and request.method.upper() not in allowed_methods:
                return view(request, *args, **kwargs)

            identity = _client_identity(request)
            digest = hashlib.sha256(f"{limiter_scope}:{identity}".encode()).hexdigest()
            key = f"rate-limit:{digest}"
            if cache.add(key, 1, timeout=window):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=window)
                    count = 1

            if count > limit:
                headers = {"Retry-After": str(window)}
                if request.path.startswith(("/ajax/", "/chatbot/", "/payment/mpesa/callback/", "/payment/stripe/webhook/")):
                    response = JsonResponse(
                        {"ok": False, "error": "Too many requests. Please try again shortly."},
                        status=429,
                    )
                else:
                    response = HttpResponse(
                        "Too many requests. Please try again shortly.", status=429
                    )
                for name, value in headers.items():
                    response[name] = value
                return response
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
