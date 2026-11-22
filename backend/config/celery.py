import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
# Reads every CELERY_* value from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")
# Finds tasks.py files inside the installed apps (used from Phase 28)
app.autodiscover_tasks()


@app.task(name="config.ping")
def ping():
    """Temporary task to prove that Django, Redis and the worker are connected."""
    return "pong"