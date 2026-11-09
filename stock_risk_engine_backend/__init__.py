from .celery import app as celery_app

# Django loads this file when it starts. That line loads your Celery app at the same time. Without it,
# the Celery app isn’t set up when Django runs, so tasks queued from your API views (recompute, refresh prices,
# the new-holding price download) can fail or never reach the worker. In the Flutter app,
# the Recompute prediction and Refresh prices buttons would then fail or never finish.