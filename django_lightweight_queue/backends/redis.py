from __future__ import absolute_import # For 'redis'

import redis

from ..job import Job
from .. import app_settings

class RedisBackend(object):
    """
    This backend has at-most-once semantics.
    """
    def __init__(self):
        self.client = redis.StrictRedis(
            host=app_settings.REDIS_HOST,
            port=app_settings.REDIS_PORT,
        )

    def startup(self, queue):
        pass

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

    def processed_job(self, queue, worker_num, job):
        pass

    def _key(self, queue):
        if app_settings.REDIS_PREFIX:
            return '%s:django_lightweight_queue:%s' % (
                app_settings.REDIS_PREFIX,
                queue,
            )

        return 'django_lightweight_queue:%s' % queue
