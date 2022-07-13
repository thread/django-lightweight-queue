from typing import Any, Dict, List, Union, Callable, Optional, Sequence

from typing_extensions import Protocol

from django.conf import settings as django_settings

from . import constants
from .types import Logger, QueueName


class LongNameAdapter:
    def __init__(self, target: Any) -> None:
        self.target = target

    def __getattr__(self, name: str) -> Any:
        return getattr(self.target, f'{constants.SETTING_NAME_PREFIX}{name}')


class Settings(Protocol):
    WORKERS: Dict[QueueName, int]
    BACKEND: str
    LOGGER_FACTORY: Union[str, Callable[[str], Logger]]

    # Allow per-queue overrides of the backend.
    BACKEND_OVERRIDES: Dict[QueueName, str]
    MIDDLEWARE: Sequence[str]

    # Apps to ignore when looking for tasks. Apps must be specified as the dotted
    # name used in `INSTALLED_APPS`. This is expected to be useful when you need to
    # have a file called `tasks.py` within an app, but don't want
    # django-lightweight-queue to import that file.
    # Note: this _doesn't_ prevent tasks being registered from these apps.
    IGNORE_APPS: Sequence[str]

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: Optional[str]
    REDIS_PREFIX: str

    ENABLE_PROMETHEUS: bool
    # Workers will export metrics on this port, and ports following it
    PROMETHEUS_START_PORT: int

    ATOMIC_JOBS: bool


class Defaults(Settings):
    WORKERS: Dict[QueueName, int] = {}
    BACKEND = 'django_lightweight_queue.backends.synchronous.SynchronousBackend'
    LOGGER_FACTORY = 'logging.getLogger'

    BACKEND_OVERRIDES: Dict[QueueName, str] = {}
    MIDDLEWARE = ('django_lightweight_queue.middleware.logging.LoggingMiddleware',)

    IGNORE_APPS: Sequence[str] = ()

    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_PASSWORD = None
    REDIS_PREFIX = ""

    ENABLE_PROMETHEUS = False

    PROMETHEUS_START_PORT = 9300

    ATOMIC_JOBS = True


class AppSettings:
    def __init__(self, layers: List[Settings]) -> None:
        self._layers = layers

    def add_layer(self, layer: Settings) -> None:
        self._layers.append(layer)

    def __getattr__(self, name: str) -> Any:
        # reverse so that later layers override earlier ones
        for layer in reversed(self._layers):
            if hasattr(layer, name):
                return getattr(layer, name)

        raise AttributeError(f"Sorry, '{name}' is not a valid setting.")


app_settings: Settings = AppSettings(layers=[Defaults(), LongNameAdapter(django_settings)])
