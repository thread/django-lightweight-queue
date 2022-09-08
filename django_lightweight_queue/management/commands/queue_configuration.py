import warnings
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from ... import app_settings
from ...utils import get_backend, get_queue_counts, load_extra_settings
from ...constants import SETTING_NAME_PREFIX
from ...cron_scheduler import get_cron_config


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        extra_settings_group = parser.add_mutually_exclusive_group()
        extra_settings_group.add_argument(
            '--config',
            action='store',
            default=None,
            help="The path to an additional django-style config file to load "
                 "(this spelling is deprecated in favour of '--extra-settings')",
        )
        extra_settings_group.add_argument(
            '--extra-settings',
            action='store',
            default=None,
            help="The path to an additional django-style settings file to load. "
                 f"{SETTING_NAME_PREFIX}* settings discovered in this file will "
                 "override those from the default Django settings.",
        )

    def handle(self, **options: Any) -> None:
        extra_config = options.pop('config')
        if extra_config is not None:
            warnings.warn(
                "Use of '--config' is deprecated in favour of '--extra-settings'.",
                category=DeprecationWarning,
            )
            options['extra_settings'] = extra_config

        # Configuration overrides
        extra_settings = options['extra_settings']
        if extra_settings is not None:
            load_extra_settings(extra_settings)

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
