import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "securityhawk.settings")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from live.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(websocket_urlpatterns),
    }
)

# Start the HA WebSocket listener on first load
from live.startup import start_ha_listener

start_ha_listener()
