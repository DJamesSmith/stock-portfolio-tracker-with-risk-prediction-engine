from celery import shared_task

from config.application_logger import ApplicationLogger


@shared_task(name="core.tasks.ping")
def ping():
    ApplicationLogger.info("Celery ping task executed.")
    return "pong"