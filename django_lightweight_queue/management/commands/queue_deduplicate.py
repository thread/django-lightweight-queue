from typing import Any

from django.core.management.base import (
    BaseCommand,
    CommandError,
    CommandParser,
)

from ...types import QueueName
from ...utils import get_backend


class Command(BaseCommand):
    help = "Command to deduplicate tasks in a redis-backed queue"  # noqa:A003 # inherited name

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            'queue',
            action='store',
            help="The queue to deduplicate",
        )

    def handle(self, queue: QueueName, **options: Any) -> None:
        backend = get_backend(queue)

        if not hasattr(backend, 'deduplicate'):
            raise CommandError(
                "Configured backend '{}.{}' doesn't support deduplication".format(
                    type(backend).__module__,
                    type(backend).__name__,
                ),
            )

        original_size, new_size = backend.deduplicate(queue)  # type: ignore[attr-defined]

        if original_size == new_size:
            self.stdout.write(
                "No duplicate jobs detected (queue length remains {})".format(
                    original_size,
                ),
            )
        else:
            self.stdout.write(
                "Deduplication reduced the queue from {} jobs to {} job(s)".format(
                    original_size,
                    new_size,
                ),
            )
