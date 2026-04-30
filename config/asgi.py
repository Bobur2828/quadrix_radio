"""ASGI config — routes HTTP through Django and WebSocket through Channels."""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.asgi import get_asgi_application

# IMPORTANT: get_asgi_application() must be called before importing anything
# that touches Django ORM. The websocket router below imports our consumers
# which in turn import models, so we set up Django first.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from radio.routing import websocket_urlpatterns  # noqa: E402


application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': URLRouter(websocket_urlpatterns),
})
