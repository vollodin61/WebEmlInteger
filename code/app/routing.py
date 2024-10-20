from celery_progress.websockets import consumers as celery_ws_consumers
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/progress/$', consumers.ProgressConsumer.as_asgi()),
    # re_path(r'ws/progress/(?P<task_id>[\w-]+)/$', celery_ws_consumers.CeleryProgressConsumer.as_asgi()),
    # re_path(r'ws/progress/(?P<task_id>[\w-]+)/$', celery_ws_consumers.ProgressConsumer.as_asgi()),
]
