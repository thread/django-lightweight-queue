import re
import argparse
import datetime

from django.core.management.base import BaseCommand, CommandError

from ...types import QueueName
from ...utils import get_backend
from ...backends.base import BackendWithPause

DURATION_PATTERN = r'^((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?$'
TIME_FORMAT = r'%Y-%m-%dT%H:%M:%S%z'


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def parse_duration_to_time(duration: str) -> datetime.datetime:
    match = re.match(DURATION_PATTERN, duration)
    if match is None:
        raise ValueError(
            f"Unknown duration format {duration!r}. Try something like '1h2m3s'.",
        )

    delta = datetime.timedelta(
        hours=int(match['hours'] or 0),
        minutes=int(match['minutes'] or 0),
        seconds=int(match['seconds'] or 0),
    )

    return utcnow() + delta


def parse_time(date_string: str) -> datetime.datetime:
    return datetime.datetime.strptime(date_string, TIME_FORMAT)


class Command(BaseCommand):
    help = """
    Command to pause work on a redis-backed queue.

    New jobs can still be added to the queue, however no jobs will be pulled off
    the queue for processing.
    """  # noqa:A003 # inherited name

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            'queue',
            action='store',
            help="The queue to pause.",
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--for',
            dest='until',
            action='store',
            type=parse_duration_to_time,
            help=(
                "The duration to pause the queue for. Specify a value like 1h2m3s, "
                "all levels of precision are optional, so 5m and 1h are both valid."
            ),
        )
        group.add_argument(
            '--until',
            action='store',
            type=parse_time,
            help=(
                "The time at which the queue should reactivate. Specify as an "
                "ISO 8601 value, specifically one parsable via datetime.strptime "
                f"using {TIME_FORMAT.replace('%', r'%%')!r}, such as {utcnow():{TIME_FORMAT}}."
            ),
        )

    def handle(self, queue: QueueName, until: datetime.datetime, **options: object) -> None:
        if until < utcnow():
            raise CommandError("Refusing to pause until a time in the past.")

        backend = get_backend(queue)

        if not isinstance(backend, BackendWithPause):
            raise CommandError(
                "Configured backend '{}.{}' doesn't support pausing".format(
                    type(backend).__module__,
                    type(backend).__name__,
                ),
            )

        backend.pause(queue, until)

        self.stdout.write(f"Paused queue {queue} until {until.isoformat(' ')}.")
