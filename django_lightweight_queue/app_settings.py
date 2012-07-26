from django.conf import settings

def setting(suffix, default):
    return getattr(settings, 'LIGHTWEIGHT_QUEUE_%s' % suffix, default)

BACKEND = setting('BACKEND', 'django_lightweight_queue.backends.synchronous.SynchronousBackend')
MIDDLEWARE = setting('MIDDLEWARE', (
    'django_lightweight_queue.middleware.logging.LoggingMiddleware',
))

# Backend-specific settings
REDIS_HOST = setting('REDIS_HOST', '127.0.0.1')
REDIS_PORT = setting('REDIS_PORT', 6379)
