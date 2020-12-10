from typing import Optional

import redis

from .. import app_settings
from ..job import Job
from .base import BaseBackend
from ..types import QueueName, WorkerNumber


class RedisBackend(BaseBackend):
    """
    This backend has at-most-once semantics.
    """

    def __init__(self) -> None:
        self.client = redis.StrictRedis(
            host=app_settings.REDIS_HOST,
            port=app_settings.REDIS_PORT,
        )

    def enqueue(self, job: Job, queue: QueueName) -> None:
        self.client.lpush(self._key(queue), job.to_json().encode('utf-8'))

    def dequeue(self, queue: QueueName, worker_num: WorkerNumber, timeout: int) -> Optional[Job]:
        raw = self.client.brpop(self._key(queue), timeout)
        if raw is None:
            return None

        _, data = raw
        return Job.from_json(data.decode('utf-8'))

    def length(self, queue: QueueName) -> int:
        return self.client.llen(self._key(queue))

    def _key(self, queue: QueueName) -> str:
        if app_settings.REDIS_PREFIX:
            return '{}:django_lightweight_queue:{}'.format(
                app_settings.REDIS_PREFIX,
                queue,
            )

        return 'django_lightweight_queue:{}'.format(queue)
