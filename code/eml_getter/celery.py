import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eml_getter.settings')

app = Celery('eml_getter')
# app.conf.beat_schedule = {
#     'fetch-emails-every-5-minutes': {
#         'task': 'app.tasks.fetch_all_emails',
#         'schedule': 60,
#     },
# }
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


