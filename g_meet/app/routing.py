from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/call-notifications/$', consumers.CallNotificationConsumer.as_asgi()),
    re_path(r'ws/call-status/$', consumers.CallStatusConsumer.as_asgi()),
]
