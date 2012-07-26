from django.conf import settings

def setting(suffix, default):
    return getattr(settings, 'LIGHTWEIGHT_QUEUE_%s' % suffix, default)

BACKEND = setting('BACKEND', 'django_lightweight_queue.backends.synchronous.SynchronousBackend')
MIDDLEWARE = setting('MIDDLEWARE', (
    'django_lightweight_queue.middleware.logging.LoggingMiddleware',
))
