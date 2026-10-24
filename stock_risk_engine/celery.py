import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stock_risk_engine.settings")

app = Celery("stock_risk_engine")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

from config.application_logger import ApplicationLogger

ApplicationLogger.info("Celery application initialized.")