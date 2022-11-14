from typing import Any

from ... import app_settings
from ...utils import get_backend, get_queue_counts
from ...command_utils import CommandWithExtraSettings
from ...cron_scheduler import get_cron_config


class Command(CommandWithExtraSettings):
    def handle(self, **options: Any) -> None:
        super().handle_extra_settings(**options)

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
                print("{:20s}: {}".format(key, config.get(key, '-')))
