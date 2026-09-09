import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("stock_tracker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

from ..config.application_logger import ApplicationLogger

ApplicationLogger.info("Celery application initialized.")
