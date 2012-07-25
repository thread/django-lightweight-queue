from django.utils.importlib import import_module

from .utils import get_backend, get_tasks, get_middleware

backend = get_backend()

tasks = get_tasks()

middleware = get_middleware()
