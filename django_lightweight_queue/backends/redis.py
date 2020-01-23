import redis

from .. import app_settings
from ..job import Job
from .base import BaseBackend


class RedisBackend(BaseBackend):
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
        try:
            _, data = self.client.brpop(self._key(queue), timeout)

            return Job.from_json(data.decode('utf-8'))
        except TypeError:
            pass

    def length(self, queue):
        return self.client.llen(self._key(queue))

    def _key(self, queue):
        if app_settings.REDIS_PREFIX:
            return '{}:django_lightweight_queue:{}'.format(
                app_settings.REDIS_PREFIX,
                queue,
            )

        return 'django_lightweight_queue:{}'.format(queue)
