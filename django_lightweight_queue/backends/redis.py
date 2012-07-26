from __future__ import absolute_import # For 'redis'

import redis

from ..job import Job
from .. import app_settings

class RedisBackend(object):
    KEY = 'django_lightweight_queue'

    def __init__(self):
        self.client = redis.Redis(
            host=app_settings.REDIS_HOST,
            port=app_settings.REDIS_PORT,
        )

    def enqueue(self, job):
        self.client.rpush(self.KEY, job.to_json())

    def dequeue(self, timeout):
        data = self.client.blpop(self.KEY, timeout)

        if data is not None:
            return Job.from_json(data)
