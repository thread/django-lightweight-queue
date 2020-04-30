from typing import Dict, Union, Mapping, TypeVar, Callable, Sequence

from django.conf import settings

from . import constants
from .types import Logger, QueueName

T = TypeVar('T')


def setting(suffix: str, default: T) -> T:
    attr_name = '{}{}'.format(constants.SETTING_NAME_PREFIX, suffix)
    return getattr(settings, attr_name, default)


WORKERS = setting('WORKERS', {})  # type: Dict[QueueName, int]
BACKEND = setting(
    'BACKEND',
    'django_lightweight_queue.backends.synchronous.SynchronousBackend',
)  # type: str

LOGGER_FACTORY = setting(
    'LOGGER_FACTORY',
    'logging.getLogger',
)  # type: Union[str, Callable[[str], Logger]]

# Allow per-queue overrides of the backend.
BACKEND_OVERRIDES = setting('BACKEND_OVERRIDES', {})  # type: Mapping[QueueName, str]

MIDDLEWARE = setting('MIDDLEWARE', (
    'django_lightweight_queue.middleware.logging.LoggingMiddleware',
    'django_lightweight_queue.middleware.transaction.TransactionMiddleware',
))  # type: Sequence[str]

# Apps to ignore when looking for tasks. Apps must be specified as the dotted
# name used in `INSTALLED_APPS`. This is expected to be useful when you need to
# have a file called `tasks.py` within an app, but don't want
# django-lightweight-queue to import that file.
# Note: this _doesn't_ prevent tasks being registered from these apps.
IGNORE_APPS = setting('IGNORE_APPS', ())  # type: Sequence[str]

# Backend-specific settings
REDIS_HOST = setting('REDIS_HOST', '127.0.0.1')  # type: str
REDIS_PORT = setting('REDIS_PORT', 6379)  # type: int
REDIS_PREFIX = setting('REDIS_PREFIX', '')  # type: str

ENABLE_PROMETHEUS = setting('ENABLE_PROMETHEUS', False)  # type: bool
# Workers will export metrics on this port, and ports following it
PROMETHEUS_START_PORT = setting('PROMETHEUS_START_PORT', 9300)  # type: int

ATOMIC_JOBS = setting('ATOMIC_JOBS', True)  # type: bool
