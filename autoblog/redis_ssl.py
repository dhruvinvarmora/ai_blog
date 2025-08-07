import os
import ssl
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autoblog.settings')

app = Celery('autoblog')

# Custom Redis backend configuration
if settings.CELERY_BROKER_URL.startswith('rediss://'):
    app.conf.broker_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_REQUIRED,
        'ssl_ca_certs': '/etc/ssl/certs/ca-certificates.crt',
    }
    app.conf.redis_backend_use_ssl = app.conf.broker_use_ssl

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()