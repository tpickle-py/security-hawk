"""WebSocket routing configuration for the live app."""

from django.urls import path

from live.consumers import LiveStateConsumer

websocket_urlpatterns = [
    path("ws/live/<str:plan_id>/", LiveStateConsumer.as_asgi()),
    path("ws/live/", LiveStateConsumer.as_asgi()),
]
