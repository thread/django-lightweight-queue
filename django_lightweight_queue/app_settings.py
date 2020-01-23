from django.conf import settings

from . import constants


def setting(suffix, default):
    attr_name = '{}{}'.format(constants.SETTING_NAME_PREFIX, suffix)
    return getattr(settings, attr_name, default)


WORKERS = setting('WORKERS', {})
BACKEND = setting('BACKEND', 'django_lightweight_queue.backends.synchronous.SynchronousBackend')

LOGGER_FACTORY = setting('LOGGER_FACTORY', 'logging.getLogger')

# Allow per-queue overrides of the backend.
BACKEND_OVERRIDES = setting('BACKEND_OVERRIDES', {})

MIDDLEWARE = setting('MIDDLEWARE', (
    'django_lightweight_queue.middleware.logging.LoggingMiddleware',
    'django_lightweight_queue.middleware.transaction.TransactionMiddleware',
))

# Apps to ignore when looking for tasks. Apps must be specified as the dotted
# name used in `INSTALLED_APPS`. This is expected to be useful when you need to
# have a file called `tasks.py` within an app, but don't want
# django-lightweight-queue to import that file.
# Note: this _doesn't_ prevent tasks being registered from these apps.
IGNORE_APPS = setting('IGNORE_APPS', ())

# Backend-specific settings
REDIS_HOST = setting('REDIS_HOST', '127.0.0.1')
REDIS_PORT = setting('REDIS_PORT', 6379)
REDIS_PREFIX = setting('REDIS_PREFIX', '')

ENABLE_PROMETHEUS = setting('ENABLE_PROMETHEUS', False)
# Workers will export metrics on this port, and ports following it
PROMETHEUS_START_PORT = setting('PROMETHEUS_START_PORT', 9300)

ATOMIC_JOBS = setting('ATOMIC_JOBS', True)
