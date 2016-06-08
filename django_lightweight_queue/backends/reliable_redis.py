from __future__ import absolute_import # For 'redis'

import redis

from ..job import Job
from .. import app_settings

class ReliableRedisBackend(object):
    """
    This backend manages a per-queue-per-worker 'processing' queue. E.g. if we
    had a queue called 'django_lightweight_queue:things', and two workers, we
    would have:
      'django_lightweight_queue:things:processing:1'
      'django_lightweight_queue:things:processing:2'

    We enqueue tasks to the main queue via LPUSH, and workers grab jobs by
    atomically popping jobs from the tail of the main queue into their
    processing queue (via BRPOPLPUSH).

    On startup we remove all jobs from any processing queues, and move to the
    tail of the main queue, i.e. so they're processed next -- see `startup`
    below.  This is to stop losing jobs if the number of workers is lowered
    (e.g. if we had 2 workers, both are processing a job, we kill the queues
    and lower the number of workers to 1, without doing this tidy up we would
    never process the job stuck in worker 2s processing queue.)

    This backend has at-least-once semantics.
    """

    def __init__(self):
        self.client = redis.Redis(
            host=app_settings.REDIS_HOST,
            port=app_settings.REDIS_PORT,
        )

    def startup(self, queue):
        main_queue_key = self._key(queue)

        pattern = self._prefix_key(
            'django_lightweight_queue:%s:processing:*' % queue,
        )

        processing_queue_keys = self.client.keys(pattern)

        def move_processing_jobs_to_main(pipe):
            # Collect all the data we need to add, before adding the data back
            # to the main queue of and clearing the processing queues
            # atomically, so if this crashes, we don't lose jobs
            all_data = []
            for key in processing_queue_keys:
                all_data.extend(pipe.lrange(key, 0, -1))

            if all_data or processing_queue_keys:
                pipe.multi()

            # NB we RPUSH, which means these jobs will get processed next
            if all_data:
                pipe.rpush(main_queue_key, *all_data)

            if processing_queue_keys:
                pipe.delete(*processing_queue_keys)

        # Will run the above function, WATCH-ing the processing_queue_keys. If
        # any of them change prior to transaction execution, it will abort and
        # retry.
        self.client.transaction(
            move_processing_jobs_to_main,
            processing_queue_keys,
        )

    def enqueue(self, job, queue):
        self.client.lpush(self._key(queue), job.to_json())

    def dequeue(self, queue, worker_number, timeout):
        main_queue_key = self._key(queue)
        processing_queue_key = self._processing_key(queue, worker_number)

        # Get any jobs off our 'processing' queue - but do not block doing so -
        # this is to catch the fact there may be a job already in our
        # processing queue if this worker crashed and has just been restarted.
        # NB different purpose than 'startup' method above.
        data = self.client.lindex(processing_queue_key, -1)
        if data:
            return Job.from_json(data)

        # Otherwise, block trying to move a job from the main queue into our
        # processing queue, and process it.
        data = self.client.brpoplpush(
            main_queue_key,
            processing_queue_key,
            timeout,
        )
        if data:
            return Job.from_json(data)

    def processed_job(self, queue, worker_number, job):
        data = job.to_json()

        self.client.lrem(self._processing_key(queue, worker_number), data)

    def length(self, queue):
        return self.client.llen(self._key(queue))

    def _key(self, queue):
        key = 'django_lightweight_queue:%s' % queue

        return self._prefix_key(key)

    def _processing_key(self, queue, worker_number):
        key = 'django_lightweight_queue:%s:processing:%s' % (
            queue,
            worker_number,
        )

        return self._prefix_key(key)

    def _prefix_key(self, key):
        if app_settings.REDIS_PREFIX:
            return '%s:%s' % (
                app_settings.REDIS_PREFIX,
                key,
            )

        return key
