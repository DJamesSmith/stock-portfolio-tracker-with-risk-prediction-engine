import os

from celery import Celery
from celery.signals import task_failure
from core.application_logger import ApplicationLogger


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stock_risk_engine.settings")

app = Celery("stock_risk_engine")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

@task_failure.connect
def log_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, **extra):
    ApplicationLogger.error(f"Celery task failed: task={sender.name}, task_id={task_id}, args={args}, kwargs={kwargs}, error={exception}")