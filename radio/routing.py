"""WebSocket URL routing for the radio app."""

from django.urls import re_path

from radio.consumers import LiveUploadConsumer

websocket_urlpatterns = [
    re_path(r'^ws/dj/live/(?P<broadcast_id>\d+)/$', LiveUploadConsumer.as_asgi()),
]
