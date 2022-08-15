import time
import datetime
import warnings
import importlib
import importlib.util
from typing import (
    Any,
    Set,
    cast,
    List,
    Mapping,
    Callable,
    Iterable,
    Sequence,
    Collection,
    TYPE_CHECKING,
)
from functools import lru_cache

from django.apps import apps
from django.core.exceptions import MiddlewareNotUsed
from django.utils.module_loading import module_has_submodule

from . import constants, app_settings
from .types import Logger, QueueName, WorkerNumber

if TYPE_CHECKING:
    from .backends.base import BaseBackend

_accepting_implied_queues = True

FIVE_SECONDS = datetime.timedelta(seconds=5)


def load_extra_config(file_path: str) -> None:
    # Based on https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    spec = importlib.util.spec_from_file_location('extra_settings', file_path)
    extra_settings = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(extra_settings)  # type: ignore[union-attr]

    def get_setting_names(module: object) -> Set[str]:
        return set(name for name in dir(module) if name.isupper())

    def with_prefix(names: Iterable[str]) -> Set[str]:
        return set(
            '{}{}'.format(constants.SETTING_NAME_PREFIX, name)
            for name in names
        )

    setting_names = get_setting_names(app_settings)
    extra_names = get_setting_names(extra_settings)

    unexpected_names = extra_names - with_prefix(setting_names)
    if unexpected_names:
        unexpected_str = "' ,'".join(unexpected_names)
        warnings.warn("Ignoring unexpected setting(s) '{}'.".format(unexpected_str))

    override_names = extra_names - unexpected_names
    for name in override_names:
        short_name = name[len(constants.SETTING_NAME_PREFIX):]
        setattr(app_settings, short_name, getattr(extra_settings, name))


@lru_cache()
def get_path(path: str) -> Any:
    module_name, attr = path.rsplit('.', 1)

    module = importlib.import_module(module_name)

    return getattr(module, attr)


@lru_cache()
def get_backend(queue: QueueName) -> 'BaseBackend':
    return get_path(app_settings.BACKEND_OVERRIDES.get(
        queue,
        app_settings.BACKEND,
    ))()


@lru_cache()
def get_logger(name: str) -> Logger:
    get_logger_fn = app_settings.LOGGER_FACTORY
    if not callable(get_logger_fn):
        get_logger_fn = cast(
            Callable[[str], Logger],
            get_path(app_settings.LOGGER_FACTORY),
        )
    return get_logger_fn(name)


@lru_cache()
def get_middleware() -> List[Any]:
    middleware = []

    for path in app_settings.MIDDLEWARE:
        try:
            middleware.append(get_path(path)())
        except MiddlewareNotUsed:
            pass

    return middleware


def refuse_further_implied_queues() -> None:
    global _accepting_implied_queues
    _accepting_implied_queues = False


def contribute_implied_queue_name(queue: QueueName) -> None:
    if not _accepting_implied_queues:
        raise RuntimeError(
            "Queues have already been enumerated, ensure that "
            "'contribute_implied_queue_name' is called during setup.",
        )
    app_settings.WORKERS.setdefault(queue, 1)


def get_queue_counts() -> Mapping[QueueName, int]:
    refuse_further_implied_queues()
    return app_settings.WORKERS


def get_worker_numbers(queue: QueueName) -> Collection[WorkerNumber]:
    count = get_queue_counts()[queue]
    return cast(Collection[WorkerNumber], range(1, count + 1))


def import_all_submodules(name: str, exclude: Sequence[str] = ()) -> None:
    for app_config in apps.get_app_configs():
        app_module = app_config.module

        module_name = app_module.__name__

        if module_name in exclude:
            continue

        try:
            importlib.import_module('{}.{}'.format(module_name, name))
        except ImportError:
            if module_has_submodule(app_module, name):
                raise


def load_all_tasks() -> None:
    import_all_submodules('tasks', app_settings.IGNORE_APPS)


def block_for_time(
    should_continue_blocking: Callable[[], bool],
    timeout: datetime.timedelta,
    check_frequency: datetime.timedelta = FIVE_SECONDS,
) -> bool:
    """
    Block until a cancellation function or timeout indicates otherwise.

    Returns whether or not the timeout was encountered.
    """
    if not should_continue_blocking():
        return False

    end = time.time() + timeout.total_seconds()

    while should_continue_blocking():
        now = time.time()
        if now > end:
            # timed out
            return True

        time.sleep(min(
            check_frequency.total_seconds(),
            end - now,
        ))

    return False


try:
    import setproctitle

    original_title = setproctitle.getproctitle()

    def set_process_title(*titles: str) -> None:
        setproctitle.setproctitle("{} {}".format(
            original_title,
            ' '.join('[{}]'.format(x) for x in titles),
        ))
except ImportError:
    def set_process_title(*titles: str) -> None:
        pass
