from django.apps import AppConfig

from .utils import import_all_submodules

class DjangoLightweightQueueConfig(AppConfig):
    name = 'django_lightweight_queue'

    def ready(self):
        import_all_submodules('tasks')
