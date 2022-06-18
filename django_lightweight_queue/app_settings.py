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
    _workers = None
    _backend = None
    _logger_factory = None
    _backend_overrides = None
    _middleware = None
    _ignore_apps = None
    _redis_host = None
    _redis_port = None
    _redis_password = None
    _redis_prefix = None
    _enable_prometheus = None
    _prometheus_start_port = None
    _atomic_jobs = None
    _site_url = None

    @property
    def WORKERS(self):
        if not self._workers:
            self._workers = self._get('WORKERS', {})
        return self._workers

    @WORKERS.setter
    def WORKERS(self, value):
        self._workers = value

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
        if not self._logger_factory:
            self._logger_factory = self._get(
                'LOGGER_FACTORY',
                'logging.getLogger',
            )
        return self._logger_factory  # type: Union[str, Callable[[str], Logger]]

    @LOGGER_FACTORY.setter
    def LOGGER_FACTORY(self, value):
        self._logger_factory = value

    @property
    def BACKEND_OVERRIDES(self):
        # Allow per-queue overrides of the backend.
        if not self._backend_overrides:
            self._backend_overrides = self._get('BACKEND_OVERRIDES', {})
        return self._backend_overrides  # type: Mapping[QueueName, str]

    @BACKEND_OVERRIDES.setter
    def BACKEND_OVERRIDES(self, value):
        self._backend_overrides = value

    @property
    def MIDDLEWARE(self):
        if not self._middleware:
            self._middleware = self._get('MIDDLEWARE', (
                'django_lightweight_queue.middleware.logging.LoggingMiddleware',
            ))
        return self._middleware  # type: Sequence[str]

    @MIDDLEWARE.setter
    def MIDDLEWARE(self, value):
        self._middleware = value

    @property
    def IGNORE_APPS(self):
        # Apps to ignore when looking for tasks. Apps must be specified as the dotted
        # name used in `INSTALLED_APPS`. This is expected to be useful when you need to
        # have a file called `tasks.py` within an app, but don't want
        # django-lightweight-queue to import that file.
        # Note: this _doesn't_ prevent tasks being registered from these apps.
        if not self._ignore_apps:
            self._ignore_apps = self._get('IGNORE_APPS', ())
        return self._ignore_apps  # type: Sequence[str]

    @IGNORE_APPS.setter
    def IGNORE_APPS(self, value):
        self._ignore_apps = value

    @property
    def REDIS_HOST(self):
        if not self._redis_host:
            self._redis_host = self._get('REDIS_HOST', '127.0.0.1')
        return self._redis_host  # type: str

    @REDIS_HOST.setter
    def REDIS_HOST(self, value):
        self._redis_host = value

    @property
    def REDIS_PORT(self):
        if not self._redis_port:
            self._redis_port = self._get('REDIS_PORT', 6379)
        return self._redis_port  # type: int

    @REDIS_PORT.setter
    def REDIS_PORT(self, value):
        self._redis_port = value

    @property
    def REDIS_PASSWORD(self):
        if not self._redis_password:
            self._redis_password = self._get('REDIS_PASSWORD', None)
        return self._redis_password  # type: Optional[str]

    @REDIS_PASSWORD.setter
    def REDIS_PASSWORD(self, value):
        self._redis_password = value

    @property
    def REDIS_PREFIX(self):
        if not self._redis_prefix:
            self._redis_prefix = self._get('REDIS_PREFIX', '')
        return self._redis_prefix  # type: str

    @REDIS_PREFIX.setter
    def REDIS_PREFIX(self, value):
        self._redis_prefix = value

    @property
    def ENABLE_PROMETHEUS(self):
        if not self._enable_prometheus:
            self._enable_prometheus = self._get('ENABLE_PROMETHEUS', False)
        return self._enable_prometheus  # type: bool

    @ENABLE_PROMETHEUS.setter
    def ENABLE_PROMETHEUS(self, value):
        self._enable_prometheus = value

    @property
    def PROMETHEUS_START_PORT(self):
        # Workers will export metrics on this port, and ports following it
        if not self._prometheus_start_port:
            self._prometheus_start_port = self._get('PROMETHEUS_START_PORT', 9300)
        return self._prometheus_start_port  # type: int

    @PROMETHEUS_START_PORT.setter
    def PROMETHEUS_START_PORT(self, value):
        self._prometheus_start_port = value

    @property
    def ATOMIC_JOBS(self):
        if not self._atomic_jobs:
            self._atomic_jobs = self._get('ATOMIC_JOBS', True)
        return self._atomic_jobs  # type: bool

    @ATOMIC_JOBS.setter
    def ATOMIC_JOBS(self, value):
        self._atomic_jobs = value

    @property
    def SITE_URL(self):
        if not self._site_url:
            self._site_url = self._get('SITE_URL', True)
        return self._site_url  # type: bool

    @SITE_URL.setter
    def SITE_URL(self, value):
        self._site_url = value




settings = Settings()
