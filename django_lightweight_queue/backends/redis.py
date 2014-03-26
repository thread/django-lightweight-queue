from __future__ import absolute_import # For 'redis'

import redis

from ..job import Job
from .. import app_settings

class RedisBackend(object):
    def __init__(self):
        self.client = redis.Redis(
            host=app_settings.REDIS_HOST,
            port=app_settings.REDIS_PORT,
        )

    def enqueue(self, job, queue):
        self.client.rpush(self._key(queue), job.to_json())

    def dequeue(self, queue, timeout):
        try:
            _, data = self.client.blpop(self._key(queue), timeout)

            return Job.from_json(data)
        except TypeError:
            pass

    def _key(self, queue):
        if app_settings.REDIS_PREFIX:
            return '%s:django_lightweight_queue:%s' % (
                app_settings.REDIS_PREFIX,
                queue,
            )

        return 'django_lightweight_queue:%s' % queue
