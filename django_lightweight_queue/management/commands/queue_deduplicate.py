from django.core.management.base import BaseCommand, CommandError

from ...utils import get_backend


class Command(BaseCommand):
    help = "Command to deduplicate tasks in a redis-backed queue"

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
                "Configured backend '%s.%s' doesn't support deduplication" % (
                    type(backend).__module__,
                    type(backend).__name__,
                ),
            )

        original_size, new_size = backend.deduplicate(queue)

        if original_size == new_size:
            self.stdout.write(
                "No duplicate jobs detected (queue length remains %d)" % (
                    original_size,
                ),
            )
        else:
            self.stdout.write(
                "Deduplication reduced the queue from %d jobs to %d job(s)" % (
                    original_size,
                    new_size,
                ),
            )
