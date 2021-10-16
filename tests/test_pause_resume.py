import io
import datetime
import unittest
from unittest import mock

import fakeredis
import freezegun
from django_lightweight_queue.types import QueueName
from django_lightweight_queue.utils import get_backend
from django_lightweight_queue.backends.base import BackendWithPauseResume
from django_lightweight_queue.backends.redis import RedisBackend
from django_lightweight_queue.management.commands.queue_pause import (
    parse_duration_to_time,
)

from django.core.management import (
    call_command,
    CommandError,
    get_commands,
    load_command_class,
)


class PauseResumeTests(unittest.TestCase):
    longMessage = True

    def assertPaused(self, queue: QueueName, context: str) -> None:
        self.assertTrue(
            self.backend.is_paused(queue),
            f"{queue} should be pauseed {context}",
        )

    def assertNotPaused(self, queue: QueueName, context: str) -> None:
        self.assertFalse(
            self.backend.is_paused(queue),
            f"{queue} should not be pauseed {context}",
        )

    def setUp(self) -> None:
        get_backend.cache_clear()

        redis_patch = mock.patch(
            'redis.StrictRedis',
            autospec=True,
            return_value=fakeredis.FakeStrictRedis(),
        )
        redis_patch.start()
        self.addCleanup(redis_patch.stop)

        # Arbitrary choice of backend, just needs to match the one used in tests
        self.backend: BackendWithPauseResume = RedisBackend()

        super().setUp()

    # Can't use override_settings due to the copying of the settings values into
    # module values at startup.
    @mock.patch(
        'django_lightweight_queue.app_settings.BACKEND',
        new='django_lightweight_queue.backends.redis.RedisBackend',
    )
    def test_pause_resume(self) -> None:
        QUEUE = QueueName('test-pauseable-queue')
        OTHER_QUEUE = QueueName('other-pauseable-queue')

        self.assertNotPaused(QUEUE, "initially")
        self.assertNotPaused(OTHER_QUEUE, "initially")

        when = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
        buffer = io.StringIO()
        # Work around https://code.djangoproject.com/ticket/33205 by bypassing
        # the argument processing
        queue_pause = load_command_class(get_commands()['queue_pause'], 'queue_pause')
        defaults = {'no_color': None, 'force_color': None, 'skip_checks': True}
        queue_pause.execute(QUEUE, until=when, stdout=buffer, **defaults)

        self.assertPaused(QUEUE, "after being paused")
        self.assertNotPaused(OTHER_QUEUE, f"after pausing {QUEUE}")

        self.assertIn(QUEUE, buffer.getvalue())
        self.assertIn(when.isoformat(' '), buffer.getvalue())

        call_command('queue_resume', QUEUE)

        self.assertNotPaused(QUEUE, "after being resumed")

    def test_pause_resume_unsupported_backend(self) -> None:
        QUEUE = QueueName('unsupported-queue')

        when = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
        # Work around https://code.djangoproject.com/ticket/33205 by bypassing
        # the argument processing
        queue_pause = load_command_class(get_commands()['queue_pause'], 'queue_pause')
        with self.assertRaises(CommandError):
            queue_pause.handle(QUEUE, until=when)

        with self.assertRaises(CommandError):
            call_command('queue_resume', QUEUE)

    @freezegun.freeze_time()
    def test_parse_duration(self) -> None:
        durations = [
            ('3h', datetime.timedelta(hours=3)),
            ('4m', datetime.timedelta(minutes=4)),
            ('5s', datetime.timedelta(seconds=5)),
            ('6h7s', datetime.timedelta(hours=6, seconds=7)),
            ('2m8s', datetime.timedelta(minutes=2, seconds=8)),
            ('6h7m', datetime.timedelta(hours=6, minutes=7)),
            ('6h7m8s', datetime.timedelta(hours=6, minutes=7, seconds=8)),
        ]

        now = datetime.datetime.now(datetime.timezone.utc)

        for duration, expected in durations:
            with self.subTest(duration):
                actual = parse_duration_to_time(duration) - now
                self.assertEqual(
                    expected,
                    actual,
                    f"Wrong duration parsed for {duration}",
                )
