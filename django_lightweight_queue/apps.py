from django.apps import AppConfig

from .utils import load_all_tasks


class DjangoLightweightQueueConfig(AppConfig):
    name = 'django_lightweight_queue'

    def ready(self) -> None:
        load_all_tasks()
