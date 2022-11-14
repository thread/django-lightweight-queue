import datetime
from typing import Optional, Collection

import redis

from .. import app_settings
from ..job import Job
from .base import BackendWithClear, BackendWithPauseResume
from ..types import QueueName, WorkerNumber
from ..utils import block_for_time


class RedisBackend(BackendWithPauseResume, BackendWithClear):
    """
    This backend has at-most-once semantics.
    """

    def __init__(self) -> None:
        self.client = redis.StrictRedis(
            host=app_settings.REDIS_HOST,
            port=app_settings.REDIS_PORT,
            password=app_settings.REDIS_PASSWORD,
        )

    def enqueue(self, job: Job, queue: QueueName) -> None:
        return self.bulk_enqueue([job], queue)

    def bulk_enqueue(self, jobs: Collection[Job], queue: QueueName) -> None:
        self.client.lpush(
            self._key(queue),
            *(job.to_json().encode('utf-8') for job in jobs),
        )

    def dequeue(self, queue: QueueName, worker_num: WorkerNumber, timeout: int) -> Optional[Job]:
        if self.is_paused(queue):
            # Block for a while to avoid constant polling ...
            block_for_time(
                lambda: self.is_paused(queue),
                timeout=datetime.timedelta(seconds=timeout),
            )
            # ... but always indicate that we did no work
            return None

        raw = self.client.brpop(self._key(queue), timeout)
        if raw is None:
            return None

        _, data = raw
        return Job.from_json(data.decode('utf-8'))

    def length(self, queue: QueueName) -> int:
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
        return bool(self.client.exists(self._pause_key(queue)))

    def clear(self, queue: QueueName) -> None:
        self.client.delete(self._key(queue))

    def _key(self, queue: QueueName) -> str:
        if app_settings.REDIS_PREFIX:
            return '{}:django_lightweight_queue:{}'.format(
                app_settings.REDIS_PREFIX,
                queue,
            )

        return 'django_lightweight_queue:{}'.format(queue)

    def _pause_key(self, queue: QueueName) -> str:
        return self._key(queue) + ':pause'
