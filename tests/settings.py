SECRET_KEY = 'very-secret-value'

LIGHTWEIGHT_QUEUE_REDIS_PREFIX = 'tests:'

INSTALLED_APPS = [
    'django_lightweight_queue',
]

ROOT_URLCONF = 'tests.urls'

SITE_URL = 'http://localhost:8000'
