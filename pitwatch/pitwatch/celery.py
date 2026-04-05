import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pitwatch.settings")

app = Celery("pitwatch")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()