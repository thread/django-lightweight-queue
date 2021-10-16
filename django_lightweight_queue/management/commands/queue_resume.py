import argparse

from django.core.management.base import BaseCommand, CommandError

from ...types import QueueName
from ...utils import get_backend
from ...backends.base import BackendWithPauseResume


class Command(BaseCommand):
    help = """
    Command to resume work immediately on a redis-backed queue.

    This removes a pause which may be in place for the given queue, though it
    may not cause workers to resume work immediately.
    """  # noqa:A003 # inherited name

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            'queue',
            action='store',
            help="The queue to resume.",
        )

    def handle(self, queue: QueueName, **options: object) -> None:
        backend = get_backend(queue)

        if not isinstance(backend, BackendWithPauseResume):
            raise CommandError(
                "Configured backend '{}.{}' doesn't support resuming from paused".format(
                    type(backend).__module__,
                    type(backend).__name__,
                ),
            )

        backend.resume(queue)
