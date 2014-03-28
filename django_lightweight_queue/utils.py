import logging

from django.db.models import get_apps
from django.core.exceptions import MiddlewareNotUsed
from django.utils.importlib import import_module
from django.utils.functional import memoize
from django.utils.module_loading import module_has_submodule

from . import app_settings

def configure_logging(level, format, filename):
    """
    Like ``logging.basicConfig`` but we use WatchedFileHandler so that we play
    nicely with logrotate and similar tools.

    We also unconditionally remove all existing handlers.
    """

    logging.root.handlers = []

    handler = logging.StreamHandler()
    if filename:
        handler = logging.handlers.WatchedFileHandler(filename)

    handler.setFormatter(logging.Formatter(format))

    logging.root.addHandler(handler)

    if level is not None:
        logging.root.setLevel(level)

def get_path(path):
    module_name, attr = path.rsplit('.', 1)

    module = import_module(module_name)

    return getattr(module, attr)

def get_backend():
    return get_path(app_settings.BACKEND)()

def get_middleware():
    middleware = []

    for path in app_settings.MIDDLEWARE:
        try:
            middleware.append(get_path(path)())
        except MiddlewareNotUsed:
            pass

    return middleware

def import_all_submodules(name):
    for app_module in get_apps():
        parts = app_module.__name__.split('.')
        prefix, last = parts[:-1], parts[-1]

        try:
            import_module('.'.join(prefix + [name]))
        except ImportError:
            # Distinguise between tasks.py existing and failing to import
            if last == 'models':
                app_module = import_module('.'.join(prefix))

            if module_has_submodule(app_module, name):
                raise

try:
    import setproctitle

    original_title = setproctitle.getproctitle()

    def set_process_title(*titles):
        setproctitle.setproctitle("%s %s" % (
            original_title,
            ' '.join('[%s]' % x for x in titles),
        ))
except ImportError:
    def set_process_title(*titles):
        pass

get_path = memoize(get_path, {}, 1)
get_backend = memoize(get_backend, {}, 0)
get_middleware = memoize(get_middleware, {}, 0)
