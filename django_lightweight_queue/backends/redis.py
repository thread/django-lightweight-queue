from __future__ import absolute_import # For 'redis'

import redis

from django.conf import settings
from django.utils import simplejson

from ..job import Job

class RedisBackend(object):
    KEY = 'django_lightweight_queue'

    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_FEEDS_HOST,
            port=settings.REDIS_FEEDS_PORT,
        )

    def enqueue(self, job):
        self.client.rpush(self.KEY, job.to_json())

    def dequeue(self, timeout):
        data = self.client.blpop(self.KEY, timeout)

        if data is not None:
            return Job.from_json(data)
