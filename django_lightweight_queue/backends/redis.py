import datetime

import redis

from .. import app_settings
from ..job import Job
from .base import BackendWithPauseResume
from ..utils import block_for_time

QueueName = str


class RedisBackend(BackendWithPauseResume):
    """
    This backend has at-most-once semantics.
    """

    def __init__(self):
        self.client = redis.StrictRedis(
            host=app_settings.REDIS_HOST,
            port=app_settings.REDIS_PORT,
        )

    def enqueue(self, job, queue):
        self.client.lpush(self._key(queue), job.to_json().encode('utf-8'))

    def dequeue(self, queue, worker_num, timeout):
        if self.is_paused(queue):
            # Block for a while to avoid constant polling ...
            block_for_time(
                lambda: self.is_paused(queue),
                timeout=datetime.timedelta(seconds=timeout),
            )
            # ... but always indicate that we did no work
            return None

        try:
            _, data = self.client.brpop(self._key(queue), timeout)

            return Job.from_json(data.decode('utf-8'))
        except TypeError:
            pass

    def length(self, queue):
        return self.client.llen(self._key(queue))

    def pause(self, queue: QueueName, until: datetime.datetime) -> None:
        """
        Pause the given queue by setting a pause marker.
        """

        pause_key = self._pause_key(queue)

        now = datetime.datetime.now(datetime.timezone.utc)
        delta = until - now

        self.client.setex(
            pause_key,
            time=int(delta.total_seconds()),
            # Store the value for debugging, we rely on setex behaviour for
            # implementation.
            value=until.isoformat(' '),
        )

    def resume(self, queue: QueueName) -> None:
        """
        Resume the given queue by deleting the pause marker (if present).
        """
        self.client.delete(self._pause_key(queue))

    def is_paused(self, queue: QueueName) -> bool:
        return self.client.exists(self._pause_key(queue))

    def _key(self, queue):
        if app_settings.REDIS_PREFIX:
            return '{}:django_lightweight_queue:{}'.format(
                app_settings.REDIS_PREFIX,
                queue,
            )

        return 'django_lightweight_queue:{}'.format(queue)

    def _pause_key(self, queue: QueueName) -> str:
        return self._key(queue) + ':pause'
