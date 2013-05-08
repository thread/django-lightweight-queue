from django.utils.importlib import import_module
from django.core.exceptions import MiddlewareNotUsed
from django.utils.functional import memoize

from . import app_settings

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

try:
    import setproctitle

    original_title = setproctitle.getproctitle()

    def set_process_title(title):
        setproctitle.setproctitle("%s [%s]" % (original_title, title))
except ImportError:
    def set_process_title(title):
        pass

get_path = memoize(get_path, {}, 1)
get_backend = memoize(get_backend, {}, 0)
get_middleware = memoize(get_middleware, {}, 0)
