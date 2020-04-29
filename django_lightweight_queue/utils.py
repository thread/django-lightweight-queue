import imp
import warnings
import importlib
from typing import Mapping
from functools import lru_cache

from django.apps import apps
from django.core.exceptions import MiddlewareNotUsed
from django.utils.module_loading import module_has_submodule

from . import constants, app_settings

_accepting_implied_queues = True


def load_extra_config(file_path):
    extra_settings = imp.load_source('extra_settings', file_path)

    def get_setting_names(module):
        return set(name for name in dir(module) if name.isupper())

    def with_prefix(names):
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
def get_path(path):
    module_name, attr = path.rsplit('.', 1)

    module = importlib.import_module(module_name)

    return getattr(module, attr)


@lru_cache()
def get_backend(queue):
    return get_path(app_settings.BACKEND_OVERRIDES.get(
        queue,
        app_settings.BACKEND,
    ))()


@lru_cache()
def get_logger(name):
    get_logger_fn = app_settings.LOGGER_FACTORY
    if not callable(get_logger_fn):
        get_logger_fn = get_path(app_settings.LOGGER_FACTORY)
    return get_logger_fn(name)


@lru_cache()
def get_middleware():
    middleware = []

    for path in app_settings.MIDDLEWARE:
        try:
            middleware.append(get_path(path)())
        except MiddlewareNotUsed:
            pass

    return middleware


def refuse_further_implied_queues():
    # type: () -> None
    global _accepting_implied_queues
    _accepting_implied_queues = False


def contribute_implied_queue_name(queue):
    # type: (str) -> None
    if not _accepting_implied_queues:
        raise RuntimeError(
            "Queues have already been enumerated, ensure that "
            "'contribute_implied_queue_name' is called during setup.",
        )
    app_settings.WORKERS.setdefault(queue, 1)


def get_queue_counts():
    # type: (None) -> Mapping[str, int]
    refuse_further_implied_queues()
    return app_settings.WORKERS


def import_all_submodules(name, exclude=()):
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


def load_all_tasks():
    import_all_submodules('tasks', app_settings.IGNORE_APPS)


try:
    import setproctitle

    original_title = setproctitle.getproctitle()

    def set_process_title(*titles):
        setproctitle.setproctitle("{} {}".format(
            original_title,
            ' '.join('[{}]'.format(x) for x in titles),
        ))
except ImportError:
    def set_process_title(*titles):
        pass
