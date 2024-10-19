import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eml_getter.settings')

app = Celery('eml_getter')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
