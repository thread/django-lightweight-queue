import django

from .task import task, TaskWrapper
from .utils import contribute_implied_queue_name

if django.VERSION < (3, 2):
    default_app_config = 'django_lightweight_queue.apps.DjangoLightweightQueueConfig'

__all__ = (
    'task',
    'TaskWrapper',
    'contribute_implied_queue_name',
)
