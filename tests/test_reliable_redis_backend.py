import datetime
import unittest

from django_lightweight_queue.job import Job
from django_lightweight_queue.backends.reliable_redis import \
    ReliableRedisBackend

from . import settings
from .mixins import RedisCleanupMixin


class ReliableRedisDeduplicationTests(RedisCleanupMixin, unittest.TestCase):
    longMessage = True
    prefix = settings.LIGHTWEIGHT_QUEUE_REDIS_PREFIX

    def create_job(self, path='path', args=('args',), kwargs=None, timeout=None, sigkill_on_stop=False, created_time=None):
        if created_time is None:
            created_time = self.start_time

        job = Job(path, args, kwargs, timeout, sigkill_on_stop)
        job.created_time = created_time

        return job

    def enqueue_job(self, queue, *args, **kwargs):
        job = self.create_job(*args, **kwargs)
        self.backend.enqueue(job, queue)
        return job

    def setUp(self):
        self.backend = ReliableRedisBackend()
        self.client = self.backend.client

        super(ReliableRedisDeduplicationTests, self).setUp()

        self.start_time = datetime.datetime.utcnow()

    def test_empty_queue(self):
        result = self.backend.deduplicate('empty-queue')
        self.assertEqual(
            (0, 0),
            result,
            "Should do nothing when queue empty",
        )

    def test_single_entry_in_queue(self):
        QUEUE = 'single-job-queue'

        self.enqueue_job(QUEUE)

        # sanity check
        self.assertEqual(
            1,
            self.backend.length(QUEUE),
        )

        result = self.backend.deduplicate(QUEUE)
        self.assertEqual(
            (1, 1),
            result,
            "Should do nothing when queue has only unique jobs",
        )

        self.assertEqual(
            1,
            self.backend.length(QUEUE),
            "Should still be a single entry in the queue"
        )

    def test_unique_entries_in_queue(self):
        QUEUE = 'unique-jobs-queue'

        self.enqueue_job(QUEUE, args=('args1',))
        self.enqueue_job(QUEUE, args=('args2',))

        # sanity check
        self.assertEqual(
            2,
            self.backend.length(QUEUE),
        )

        result = self.backend.deduplicate(QUEUE)
        self.assertEqual(
            (2, 2),
            result,
            "Should do nothing when queue has only unique jobs",
        )

        self.assertEqual(
            2,
            self.backend.length(QUEUE),
            "Should still be a single entry in the queue"
        )

    def test_duplicate_entries_in_queue(self):
        QUEUE = 'duplicate-jobs-queue'

        self.enqueue_job(QUEUE)
        self.enqueue_job(QUEUE)

        # sanity check
        self.assertEqual(
            2,
            self.backend.length(QUEUE),
        )

        result = self.backend.deduplicate(QUEUE)
        self.assertEqual(
            (2, 1),
            result,
            "Should remove duplicate entries from queue",
        )

        self.assertEqual(
            1,
            self.backend.length(QUEUE),
            "Should still be a single entry in the queue"
        )

    def test_preserves_order_with_fixed_timestamps(self):
        QUEUE = 'job-queue'
        WORKER_NUMBER = 0

        self.enqueue_job(QUEUE, args=['args1'])
        self.enqueue_job(QUEUE, args=['args2'])
        self.enqueue_job(QUEUE, args=['args1'])
        self.enqueue_job(QUEUE, args=['args3'])
        self.enqueue_job(QUEUE, args=['args2'])
        self.enqueue_job(QUEUE, args=['args1'])

        # sanity check
        self.assertEqual(
            6,
            self.backend.length(QUEUE),
        )

        result = self.backend.deduplicate(QUEUE)
        self.assertEqual(
            (6, 3),
            result,
            "Should remove duplicate entries from queue",
        )

        self.assertEqual(
            3,
            self.backend.length(QUEUE),
            "Wrong number of jobs remaining in queue"
        )

        job = self.backend.dequeue(QUEUE, WORKER_NUMBER, timeout=1)
        self.assertEqual(
            ['args1'],
            job.args,
            "First job dequeued should be the first job enqueued",
        )

        self.backend.processed_job(QUEUE, WORKER_NUMBER, job)

        job = self.backend.dequeue(QUEUE, WORKER_NUMBER, timeout=1)
        self.assertEqual(
            ['args2'],
            job.args,
            "Second job dequeued should be the second job enqueued",
        )

        self.backend.processed_job(QUEUE, WORKER_NUMBER, job)

        job = self.backend.dequeue(QUEUE, WORKER_NUMBER, timeout=1)
        self.assertEqual(
            ['args3'],
            job.args,
            "Third job dequeued should be the third job enqueued",
        )

    def test_preserves_order_with_unique_timestamps(self):
        QUEUE = 'job-queue'
        WORKER_NUMBER = 0

        time = self.start_time
        self.enqueue_job(QUEUE, args=['args1'], created_time=time)

        time += datetime.timedelta(seconds=1)
        self.enqueue_job(QUEUE, args=['args2'], created_time=time)

        time += datetime.timedelta(seconds=1)
        self.enqueue_job(QUEUE, args=['args1'], created_time=time)

        time += datetime.timedelta(seconds=1)
        self.enqueue_job(QUEUE, args=['args3'], created_time=time)

        time += datetime.timedelta(seconds=1)
        self.enqueue_job(QUEUE, args=['args2'], created_time=time)

        time += datetime.timedelta(seconds=1)
        self.enqueue_job(QUEUE, args=['args1'], created_time=time)

        # sanity check
        self.assertEqual(
            6,
            self.backend.length(QUEUE),
        )

        result = self.backend.deduplicate(QUEUE)
        self.assertEqual(
            (6, 3),
            result,
            "Should remove duplicate entries from queue",
        )

        self.assertEqual(
            3,
            self.backend.length(QUEUE),
            "Wrong number of jobs remaining in queue"
        )

        job = self.backend.dequeue(QUEUE, WORKER_NUMBER, timeout=1)
        self.assertEqual(
            ['args1'],
            job.args,
            "First job dequeued should be the first job enqueued",
        )

        self.backend.processed_job(QUEUE, WORKER_NUMBER, job)

        job = self.backend.dequeue(QUEUE, WORKER_NUMBER, timeout=1)
        self.assertEqual(
            ['args2'],
            job.args,
            "Second job dequeued should be the second job enqueued",
        )

        self.backend.processed_job(QUEUE, WORKER_NUMBER, job)

        job = self.backend.dequeue(QUEUE, WORKER_NUMBER, timeout=1)
        self.assertEqual(
            ['args3'],
            job.args,
            "Third job dequeued should be the third job enqueued",
        )
