from django.conf import settings

def setting(suffix, default):
    return getattr(settings, 'SIMPLE_QUEUE_%s' % suffix, default)

BACKEND = setting('BACKED', 'django_lightweight_queue.backends.synchronous.SynchronousBackend')
MIDDLEWARE = setting('MIDDLEWARE', (
    'django_lightweight_queue.middleware.logging.LoggingMiddleware',
))
