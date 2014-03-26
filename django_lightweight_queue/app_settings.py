from django.conf import settings

def setting(suffix, default):
    return getattr(settings, 'LIGHTWEIGHT_QUEUE_%s' % suffix, default)

WORKERS = setting('WORKERS', {})
BACKEND = setting('BACKEND', 'django_lightweight_queue.backends.synchronous.SynchronousBackend')
MIDDLEWARE = setting('MIDDLEWARE', (
    'django_lightweight_queue.middleware.logging.LoggingMiddleware',
    'django_lightweight_queue.middleware.transaction.TransactionMiddleware',
))

# Backend-specific settings
REDIS_HOST = setting('REDIS_HOST', '127.0.0.1')
REDIS_PORT = setting('REDIS_PORT', 6379)
REDIS_PREFIX = setting('REDIS_PREFIX', '')
