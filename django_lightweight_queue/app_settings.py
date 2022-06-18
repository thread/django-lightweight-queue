from typing import Union, Mapping, TypeVar, Callable, Optional, Sequence

from django.conf import settings as django_settings

from . import constants
from .types import Logger, QueueName

T = TypeVar('T')


class Settings():
    def _get(self, suffix: str, default: T) -> T:
        attr_name = '{}{}'.format(constants.SETTING_NAME_PREFIX, suffix)
        return getattr(django_settings, attr_name, default)

    # adjustable values at runtime
    _backend = None
    _redis_password = None

    @property
    def WORKERS(self):
        return self._get('WORKERS', {})

    @property
    def BACKEND(self):
        if not self._backend:
            self._backend = self._get(
                'BACKEND',
                'django_lightweight_queue.backends.synchronous.SynchronousBackend',
            )
        return self._backend  # type: str

    @BACKEND.setter
    def BACKEND(self, value):
        self._backend = value

    @property
    def LOGGER_FACTORY(self):
        return self._get(
            'LOGGER_FACTORY',
            'logging.getLogger',
        )  # type: Union[str, Callable[[str], Logger]]

    @property
    def BACKEND_OVERRIDES(self):
        # Allow per-queue overrides of the backend.
        return self._get('BACKEND_OVERRIDES', {})  # type: Mapping[QueueName, str]

    @property
    def MIDDLEWARE(self):
        return self._get('MIDDLEWARE', (
            'django_lightweight_queue.middleware.logging.LoggingMiddleware',
        ))  # type: Sequence[str]

    @property
    def IGNORE_APPS(self):
        # Apps to ignore when looking for tasks. Apps must be specified as the dotted
        # name used in `INSTALLED_APPS`. This is expected to be useful when you need to
        # have a file called `tasks.py` within an app, but don't want
        # django-lightweight-queue to import that file.
        # Note: this _doesn't_ prevent tasks being registered from these apps.
        return self._get('IGNORE_APPS', ())  # type: Sequence[str]

    @property
    def REDIS_HOST(self):
        return self._get('REDIS_HOST', '127.0.0.1')  # type: str

    @property
    def REDIS_PORT(self):
        return self._get('REDIS_PORT', 6379)  # type: int

    @property
    def REDIS_PASSWORD(self):
        return self._get('REDIS_PASSWORD', None)  # type: Optional[str]

    @property
    def REDIS_PREFIX(self):
        return self._get('REDIS_PREFIX', '')  # type: str

    @property
    def ENABLE_PROMETHEUS(self):
        return self._get('ENABLE_PROMETHEUS', False)  # type: bool

    @property
    def PROMETHEUS_START_PORT(self):
        # Workers will export metrics on this port, and ports following it
        return self._get('PROMETHEUS_START_PORT', 9300)  # type: int

    @property
    def ATOMIC_JOBS(self):
        return self._get('ATOMIC_JOBS', True)  # type: bool


settings = Settings()
