from django.conf import settings

from . import constants

def setting(suffix, default):
    attr_name = '%s%s' % (constants.SETTING_NAME_PREFIX, suffix)
    return getattr(settings, attr_name, default)

WORKERS = setting('WORKERS', {})
BACKEND = setting('BACKEND', 'django_lightweight_queue.backends.synchronous.SynchronousBackend')

# Allow per-queue overrides of the backend.
BACKEND_OVERRIDES = setting('BACKEND_OVERRIDES', {})

MIDDLEWARE = setting('MIDDLEWARE', (
    'django_lightweight_queue.middleware.logging.LoggingMiddleware',
    'django_lightweight_queue.middleware.transaction.TransactionMiddleware',
))

# Backend-specific settings
REDIS_HOST = setting('REDIS_HOST', '127.0.0.1')
REDIS_PORT = setting('REDIS_PORT', 6379)
REDIS_PREFIX = setting('REDIS_PREFIX', '')

ENABLE_PROMETHEUS = setting('ENABLE_PROMETHEUS', False)
# Workers will export metrics on this port, and ports following it
PROMETHEUS_START_PORT = setting('PROMETHEUS_START_PORT', 9300)
