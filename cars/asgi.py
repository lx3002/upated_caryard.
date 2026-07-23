import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import caryard.routing  # use caryard’s routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cars.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            caryard.routing.websocket_urlpatterns
        )
    ),
})

