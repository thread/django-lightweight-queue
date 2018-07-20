from .task import task, TaskWrapper

default_app_config = 'django_lightweight_queue.apps.DjangoLightweightQueueConfig'

__all__ = (
    'task',
    'TaskWrapper',
)
