import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autoblog.settings')

app = Celery('autoblog')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Windows-specific settings
if os.name == 'nt':
    app.conf.worker_pool = 'solo'
    app.conf.worker_concurrency = 1

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')