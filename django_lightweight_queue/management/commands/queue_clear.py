import argparse

from django.core.management.base import BaseCommand, CommandError

from ...types import QueueName
from ...utils import get_backend
from ...backends.base import BackendWithClear


class Command(BaseCommand):
    help = """
    Command to clear work on a redis-backed queue.

    All pending jobs will be deleted from the queue. In flight jobs won't be
    affected.
    """  # noqa:A003 # inherited name

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            'queue',
            action='store',
            help="The queue to pause.",
        )

        parser.add_argument(
            '--yes',
            dest='skip_prompt',
            action='store_true',
            help="Skip confirmation prompt.",
        )

    def handle(self, queue: QueueName, skip_prompt: bool = False, **options: object) -> None:

        backend = get_backend(queue)

        if not isinstance(backend, BackendWithClear):
            raise CommandError(
                "Configured backend '{}.{}' doesn't support clearing".format(
                    type(backend).__module__,
                    type(backend).__name__,
                ),
            )

        if not skip_prompt:
            prompt = "Clear all jobs from queue {}) [y/N] ".format(queue)
            choice = input(prompt).lower()

            if choice != "y":
                raise CommandError("Aborting")

        backend.clear(queue)
