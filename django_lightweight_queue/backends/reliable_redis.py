import datetime
from typing import Dict, List, Tuple, TypeVar, Optional, Collection

import redis

from .. import app_settings
from ..job import Job
from .base import (
    BackendWithClear,
    BackendWithDeduplicate,
    BackendWithPauseResume,
)
from ..types import QueueName, WorkerNumber
from ..utils import block_for_time, get_worker_numbers
from ..progress_logger import ProgressLogger, NULL_PROGRESS_LOGGER

# Work around https://github.com/python/mypy/issues/9914. Name needs to match
# that in progress_logger.py.
T = TypeVar('T')


class ReliableRedisBackend(BackendWithClear, BackendWithDeduplicate, BackendWithPauseResume):
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

    def __init__(self) -> None:
        self.client = redis.StrictRedis(
            host=app_settings.REDIS_HOST,
            port=app_settings.REDIS_PORT,
            password=app_settings.REDIS_PASSWORD,
            db=app_settings.REDIS_DATABASE,
        )

    def startup(self, queue: QueueName) -> None:
        main_queue_key = self._key(queue)

        pattern = self._prefix_key(
            'django_lightweight_queue:{}:processing:*'.format(queue),
        )

        # Work out which processing queues no longer have associated workers.
        # Without this the startup process can end up racing against workers on
        # other machines which are validly re-populating their processing queues
        # as they work on jobs.
        current_processing_queue_keys = set(self.client.keys(pattern))
        expected_processing_queue_keys = set(
            self._processing_key(queue, worker_number).encode()
            for worker_number in get_worker_numbers(queue)
        )
        processing_queue_keys = current_processing_queue_keys - expected_processing_queue_keys

        def move_processing_jobs_to_main(pipe: 'redis.StrictRedis[bytes]') -> None:
            # Note: the `pipe` argument here is actually a Pipeline (strictly
            # `redis.client.Pipeline[bytes]`), however it's not the usual
            # late-executing pipeline that might be expected (or that the
            # typeshed expects) so we pretend that it's a StrictRedis instance
            # to get the type checking to *mostly* work. See typeshed issue
            # https://github.com/python/typeshed/issues/6028 for more details.

            # Collect all the data we need to add, before adding the data back
            # to the main queue of and clearing the processing queues
            # atomically, so if this crashes, we don't lose jobs
            all_data: List[bytes] = []
            for key in processing_queue_keys:
                all_data.extend(pipe.lrange(key, 0, -1))

            if all_data or processing_queue_keys:
                pipe.multi()  # type: ignore[attr-defined] # see explanation above

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
            *processing_queue_keys,
        )

    def enqueue(self, job: Job, queue: QueueName) -> None:
        return self.bulk_enqueue([job], queue)

    def bulk_enqueue(self, jobs: Collection[Job], queue: QueueName) -> None:
        self.client.lpush(
            self._key(queue),
            *(job.to_json().encode('utf-8') for job in jobs),
        )

    def dequeue(self, queue: QueueName, worker_number: WorkerNumber, timeout: int) -> Optional[Job]:
        main_queue_key = self._key(queue)
        processing_queue_key = self._processing_key(queue, worker_number)

        if self.is_paused(queue):
            # Block for a while to avoid constant polling ...
            block_for_time(
                lambda: self.is_paused(queue),
                timeout=datetime.timedelta(seconds=timeout),
            )
            # ... but always indicate that we did no work
            return None

        # Get any jobs off our 'processing' queue - but do not block doing so -
        # this is to catch the fact there may be a job already in our
        # processing queue if this worker crashed and has just been restarted.
        # NB different purpose than 'startup' method above.
        data = self.client.lindex(processing_queue_key, -1)
        if data:
            return Job.from_json(data.decode('utf-8'))

        # Otherwise, block trying to move a job from the main queue into our
        # processing queue, and process it.
        data = self.client.brpoplpush(
            main_queue_key,
            processing_queue_key,
            timeout,
        )
        if data:
            return Job.from_json(data.decode('utf-8'))

        return None

    def processed_job(self, queue: QueueName, worker_number: WorkerNumber, job: Job) -> None:
        data = job.to_json().encode('utf-8')

        self.client.lrem(
            self._processing_key(queue, worker_number),
            count=1,
            value=data,
        )

    def length(self, queue: QueueName) -> int:
        return self.client.llen(self._key(queue))

    def deduplicate(
        self,
        queue: QueueName,
        *,
        progress_logger: ProgressLogger = NULL_PROGRESS_LOGGER
    ) -> Tuple[int, int]:
        """
        Deduplicate the given queue by comparing the jobs in a manner which
        ignores their created timestamps.

        We use ``Job.identity_without_created`` to collect up jobs which would
        be identical when run but potentially different by timestamp. We then
        remove all but the first (oldest) of those jobs one at a time.

        Returns a tuple of (original_size, new_size) of the queue.
        """

        main_queue_key = self._key(queue)

        original_size = self.client.llen(main_queue_key)

        if not original_size:
            return 0, 0

        # A mapping of job_identity -> list of raw_job data; the entries in the
        # latter list are ordered from newest to oldest
        jobs = {}  # type: Dict[str, List[bytes]]

        progress_logger.info("Collecting jobs")

        for raw_data in progress_logger.progress(self.client.lrange(main_queue_key, 0, -1)):
            job_identity = Job.from_json(
                raw_data.decode('utf-8'),
            ).identity_without_created()

            jobs.setdefault(job_identity, []).append(raw_data)

        progress_logger.info("Removing duplicate jobs")

        for raw_jobs in progress_logger.progress(jobs.values()):
            # Leave the oldest in the queue
            for raw_data in raw_jobs[:-1]:
                # Remove only one instance of this data (thus coping with
                # unlikely but possible non-unique entries)
                self.client.lrem(
                    main_queue_key,
                    value=raw_data,
                    count=1,
                )

        return original_size, self.client.llen(main_queue_key)

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
        key = 'django_lightweight_queue:{}'.format(queue)

        return self._prefix_key(key)

    def _pause_key(self, queue: QueueName) -> str:
        return self._key(queue) + ':pause'

    def _processing_key(self, queue: QueueName, worker_number: WorkerNumber) -> str:
        key = 'django_lightweight_queue:{}:processing:{}'.format(
            queue,
            worker_number,
        )

        return self._prefix_key(key)

    def _prefix_key(self, key: str) -> str:
        if app_settings.REDIS_PREFIX:
            return '{}:{}'.format(
                app_settings.REDIS_PREFIX,
                key,
            )

        return key
