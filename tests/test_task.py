import unittest
import contextlib
from typing import Any, Mapping, Iterator
from unittest import mock

import fakeredis
from django_lightweight_queue import task
from django_lightweight_queue.types import QueueName, WorkerNumber
from django_lightweight_queue.utils import get_path, get_backend
from django_lightweight_queue.backends.redis import RedisBackend

from . import settings

QUEUE = QueueName('dummy-queue')


@task(str(QUEUE))
def dummy_task(num: int) -> None:
    pass


class TaskTests(unittest.TestCase):
    longMessage = True
    prefix = settings.LIGHTWEIGHT_QUEUE_REDIS_PREFIX

    @contextlib.contextmanager
    def mock_workers(self, workers: Mapping[str, int]) -> Iterator[None]:
        with unittest.mock.patch(
            'django_lightweight_queue.utils._accepting_implied_queues',
            new=False,
        ), unittest.mock.patch.dict(
            'django_lightweight_queue.app_settings.WORKERS',
            workers,
        ):
            yield

    def setUp(self) -> None:
        super().setUp()

        get_backend.cache_clear()

        with mock.patch('redis.StrictRedis', fakeredis.FakeStrictRedis):
            self.backend = RedisBackend()

        # Mock get_backend. Unfortunately due to the nameing of the 'task'
        # decorator class being the same as its containing module and it being
        # exposed as the symbol at django_lightweight_queue.task, we cannot mock
        # this in the normal way. Instead we mock get_path (which get_backend
        # calls) and intercept the our dummy value.
        def mocked_get_path(path: str) -> Any:
            if path == 'test-backend':
                return lambda: self.backend
            return get_path(path)

        patch = mock.patch(
            'django_lightweight_queue.app_settings.BACKEND',
            new='test-backend',
        )
        patch.start()
        self.addCleanup(patch.stop)
        patch = mock.patch(
            'django_lightweight_queue.utils.get_path',
            side_effect=mocked_get_path,
        )
        patch.start()
        self.addCleanup(patch.stop)

    def tearDown(self) -> None:
        super().tearDown()
        get_backend.cache_clear()

    def test_enqueues_job(self) -> None:
        self.assertEqual(0, self.backend.length(QUEUE))

        dummy_task(42)

        job = self.backend.dequeue(QUEUE, WorkerNumber(0), 5)
        # Plain assert to placate mypy
        assert job is not None, "Failed to get a job after enqueuing one"

        self.assertEqual(
            {
                'path': 'tests.test_task.dummy_task',
                'args': [42],
                'kwargs': {},
                'timeout': None,
                'sigkill_on_stop': False,
                'created_time': mock.ANY,
            },
            job.as_dict(),
        )

    def test_bulk_enqueues_jobs(self) -> None:
        self.assertEqual(0, self.backend.length(QUEUE))

        with dummy_task.bulk_enqueue() as enqueue:
            enqueue(13)
            enqueue(num=42)

        job = self.backend.dequeue(QUEUE, WorkerNumber(0), 5)
        # Plain assert to placate mypy
        assert job is not None, "Failed to get a job after enqueuing one"

        self.assertEqual(
            {
                'path': 'tests.test_task.dummy_task',
                'args': [13],
                'kwargs': {},
                'timeout': None,
                'sigkill_on_stop': False,
                'created_time': mock.ANY,
            },
            job.as_dict(),
            "First job",
        )

        job = self.backend.dequeue(QUEUE, WorkerNumber(0), 5)
        # Plain assert to placate mypy
        assert job is not None, "Failed to get a job after enqueuing one"

        self.assertEqual(
            {
                'path': 'tests.test_task.dummy_task',
                'args': [],
                'kwargs': {'num': 42},
                'timeout': None,
                'sigkill_on_stop': False,
                'created_time': mock.ANY,
            },
            job.as_dict(),
            "Second job",
        )
