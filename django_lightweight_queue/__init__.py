from .task import task, TaskWrapper
from .utils import contribute_implied_queue_name

default_app_config = 'django_lightweight_queue.apps.DjangoLightweightQueueConfig'

__all__ = (
    'task',
    'TaskWrapper',
    'contribute_implied_queue_name',
)
