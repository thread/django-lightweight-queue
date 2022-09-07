import importlib
from typing import Optional
from pathlib import Path

from django.test import SimpleTestCase

from django_lightweight_queue import app_settings
from django_lightweight_queue.job import Job
from django_lightweight_queue.types import QueueName, WorkerNumber
from django_lightweight_queue.utils import get_backend, load_extra_settings
from django_lightweight_queue.backends.base import BaseBackend

TESTS_DIR = Path(__file__).parent


class TestBackend(BaseBackend):
    def enqueue(self, job: Job, queue: QueueName) -> None:
        pass

    def dequeue(self, queue: QueueName, worker_num: WorkerNumber, timeout: int) -> Optional[Job]:
        pass

    def length(self, queue: QueueName) -> int:
        pass


class ExtraSettingsTests(SimpleTestCase):
    def setUp(self) -> None:
        get_backend.cache_clear()
        super().setUp()

    def tearDown(self) -> None:
        importlib.reload(app_settings)
        get_backend.cache_clear()
        super().tearDown()

    def test_updates_settings(self) -> None:
        load_extra_settings(str(TESTS_DIR / '_demo_extra_settings.py'))

        backend = get_backend('test-queue')
        self.assertIsInstance(backend, TestBackend)

        self.assertEqual('a very bad password', app_settings.REDIS_PASSWORD)

    def test_warns_about_unexpected_settings(self) -> None:
        with self.assertWarnsRegex(Warning, r'Ignoring unexpected setting.+\bNOT_REDIS_PASSWORD\b'):
            load_extra_settings(str(TESTS_DIR / '_demo_extra_settings_unexpected.py'))

        self.assertEqual('expected', app_settings.REDIS_PASSWORD)

    def test_updates_settings_with_falsey_values(self) -> None:
        load_extra_settings(str(TESTS_DIR / '_demo_extra_settings.py'))
        load_extra_settings(str(TESTS_DIR / '_demo_extra_settings_falsey.py'))

        self.assertIsNone(app_settings.REDIS_PASSWORD)
        self.assertFalse(app_settings.ATOMIC_JOBS)

    def test_rejects_missing_file(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_extra_settings(str(TESTS_DIR / '_no_such_file.py'))
