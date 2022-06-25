import io
import unittest
import contextlib
import urllib.parse
from unittest import mock

from django.http import QueryDict
from django.urls import resolve

from django_lightweight_queue import task
from django_lightweight_queue.job import Job
from django_lightweight_queue.types import QueueName
from django_lightweight_queue.backends.debug_web import DebugWebBackend


@task()
def demo_task() -> None:
    pass


class DebugWebBackendTests(unittest.TestCase):
    def test_enqueue_prints_valid_url(self) -> None:
        backend = DebugWebBackend()

        job = Job('tests.test_debug_web_backend.demo_task', ('positional',), {'keyword': '&arg='})

        with mock.patch('tests.test_debug_web_backend.demo_task') as demo_task_mock:
            with contextlib.redirect_stdout(io.StringIO()) as mock_stdout:
                backend.enqueue(job, QueueName('test-queue'))

        url = mock_stdout.getvalue().strip()
        parse_result = urllib.parse.urlparse(url)

        match = resolve(parse_result.path)
        self.assertIsNotNone(match, f"Failed to match {parse_result.path}")

        query = QueryDict(parse_result.query)

        self.assertEqual(
            {'job': [job.to_json()]},
            dict(query),
            "Wrong query arguments printed",
        )

        demo_task_mock.assert_not_called()
