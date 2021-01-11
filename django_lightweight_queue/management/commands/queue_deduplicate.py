from typing import TypeVar

from django.core.management.base import BaseCommand, CommandError

from ...utils import get_backend
from ...progress_logger import ProgressLogger

T = TypeVar('T')


class Command(BaseCommand):
    help = "Command to deduplicate tasks in a redis-backed queue"  # noqa:A003 # inherited name

    def add_arguments(self, parser):
        parser.add_argument(
            'queue',
            action='store',
            help="The queue to deduplicate",
        )

    def handle(self, queue, **options):
        backend = get_backend(queue)

        if not hasattr(backend, 'deduplicate'):
            raise CommandError(
                "Configured backend '{}.{}' doesn't support deduplication".format(
                    type(backend).__module__,
                    type(backend).__name__,
                ),
            )

        original_size, new_size = backend.deduplicate(
            queue,
            progress_logger=self.get_progress_logger(),
        )

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

    def get_progress_logger(self) -> ProgressLogger:
        try:
            import tqdm
            progress = tqdm.tqdm
        except ImportError:
            def progress(iterable: T) -> T:
                return iterable

        return ProgressLogger(self.stdout.write, progress)
