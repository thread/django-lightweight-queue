from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from ... import app_settings
from ...utils import get_backend, get_queue_counts, load_extra_config
from ...cron_scheduler import get_cron_config


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--config',
            action='store',
            default=None,
            help="The path to an additional django-style config file to load",
        )

    def handle(self, **options: Any) -> None:
        # Configuration overrides
        extra_config = options['config']
        if extra_config is not None:
            load_extra_config(extra_config)

        print("django-lightweight-queue")
        print("========================")
        print("")
        print("{0:<55} {1:<5} {2}".format("Queue name", "Concurrency", "Backend"))
        print("-" * 27)

        for k, v in sorted(get_queue_counts().items()):
            print(" {0:<54} {1:<5} {2}".format(
                k,
                v,
                get_backend(k).__class__.__name__,
            ))

        print("")
        print("Middleware:")
        for x in app_settings.MIDDLEWARE:
            print(" * {}".format(x))

        print("")
        print("Cron configuration")

        for config in get_cron_config():
            print("")
            for key in (
                'command',
                'command_args',
                'hours',
                'minutes',
                'queue',
                'timeout',
                'sigkill_on_stop',
            ):
                print("{:20s}: {}".format(key, config.get(k, '-')))
