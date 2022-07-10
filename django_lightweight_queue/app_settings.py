from typing import Any, Dict, Union, Callable, Optional, Sequence

from django.conf import settings as django_settings

from . import constants
from .types import Logger, QueueName


class Settings:
    _uses_short_names: bool = True  # used later in checking for values


class Defaults(Settings):
    WORKERS: Dict[QueueName, int] = {}
    BACKEND: str = 'django_lightweight_queue.backends.synchronous.SynchronousBackend'
    LOGGER_FACTORY: Union[str, Callable[[str], Logger]] = 'logging.getLogger'
    BACKEND_OVERRIDES: Dict[QueueName, str] = {}
    MIDDLEWARE: Sequence[str] = ('django_lightweight_queue.middleware.logging.LoggingMiddleware',)
    # Apps to ignore when looking for tasks. Apps must be specified as the dotted
    # name used in `INSTALLED_APPS`. This is expected to be useful when you need to
    # have a file called `tasks.py` within an app, but don't want
    # django-lightweight-queue to import that file.
    # Note: this _doesn't_ prevent tasks being registered from these apps.
    IGNORE_APPS: Sequence[str] = ()
    REDIS_HOST: str = '127.0.0.1'
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_PREFIX: str = ""
    ENABLE_PROMETHEUS: bool = False
    # Workers will export metrics on this port, and ports following it
    PROMETHEUS_START_PORT: int = 9300
    ATOMIC_JOBS: bool = True


class AppSettings:
    def __init__(self, layers: list[Settings]) -> None:
        self._layers = layers

    def add_layer(self, layer: Settings) -> None:  # to be called by `load_extra_config`
        self._layers.append(layer)

    def __getattr__(self, name: str) -> Any:
        # reverse so that later layers override earlier ones
        for layer in reversed(self._layers):
            # check to see if the layer is internal or external
            use_short_names = getattr(layer, "_uses_short_names", False)
            attr_name = (
                '{}{}'.format(constants.SETTING_NAME_PREFIX, name)
                if use_short_names else name
            )
            if hasattr(layer, attr_name):
                return getattr(layer, attr_name)

        raise AttributeError(f"Sorry, '{name}' is not a valid setting.")


app_settings = AppSettings(layers=[Defaults(), django_settings])
