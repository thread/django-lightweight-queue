from typing import Any, Dict, Optional

import daemonize

from django.apps import apps
from django.core.management.base import (
    BaseCommand,
    CommandError,
    CommandParser,
)

from ...types import QueueName
from ...utils import get_logger, get_backend, get_middleware, load_extra_config
from ...runner import runner
from ...machine_types import Machine, PooledMachine, DirectlyConfiguredMachine


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--pidfile',
            action='store',
            dest='pidfile',
            default=None,
            help="Fork and write pidfile to this file.",
        )
        parser.add_argument(
            '--touchfile',
            action='store',
            dest='touchfile',
            default=None,
            help="touch(1) the specified file after running a job.",
        )
        parser.add_argument(
            '--machine',
            action='store',
            dest='machine_number',
            default=None,
            help="Machine number, for parallelism",
        )
        parser.add_argument(
            '--of',
            action='store',
            dest='machine_count',
            default=None,
            help="Total number of machines running the queues",
        )
        parser.add_argument(
            '--only-queue',
            action='store',
            default=None,
            help="Only run the given queue, useful for local debugging",
        )
        parser.add_argument(
            '--config',
            action='store',
            default=None,
            help="The path to an additional django-style config file to load",
        )
        parser.add_argument(
            '--exact-configuration',
            action='store_true',
            help="Run queues on this machine exactly as specified. Requires the"
                 " use of the '--config' option in addition. It is an error to"
                 " use this option together with either '--machine' or '--of'.",
        )

    def validate_and_normalise(self, options: Dict[str, Any]) -> None:
        if options['exact_configuration']:
            if not options['config']:
                raise CommandError(
                    "Must provide a value for '--config' when using "
                    "'--exact-configuration'.",
                )

            invalid_others = ('machine_count', 'machine_number', 'only_queue')

            if any(options[name] is not None for name in invalid_others):
                raise CommandError(
                    "Must not specify '--machine', '--of' or '--only-queue'"
                    " when using '--exact-configuration'.",
                )

        else:
            real_defaults = {
                'machine_count': 1,
                'machine_number': 1,
            }

            for name, default in real_defaults.items():
                try:
                    options[name] = int(options[name])
                except TypeError:
                    options[name] = default

            if options['machine_count'] < options['machine_number']:
                raise CommandError(
                    "Machine number must be less than or equal to machine count!",
                )

    def handle(self, **options: Any) -> None:
        logger = get_logger('dlq.master')

        self.validate_and_normalise(options)

        def touch_filename(name: str) -> Optional[str]:
            try:
                return options['touchfile'] % name
            except TypeError:
                return None

        # Configuration overrides
        extra_config = options['config']
        if extra_config is not None:
            load_extra_config(extra_config)

        logger.info("Starting queue master")

        # Ensure children will be able to import our backend
        get_backend('dummy')

        get_middleware()
        logger.debug("Loaded middleware")

        # Ensure children will be able to import most things, but also try and
        # save memory by importing as much as possible before the fork() as it
        # has copy-on-write semantics.
        apps.get_models()
        logger.debug("Loaded models")

        if options['exact_configuration']:
            machine = DirectlyConfiguredMachine()  # type: Machine
        else:
            machine = PooledMachine(
                machine_number=int(options['machine_number']),
                machine_count=int(options['machine_count']),
                only_queue=QueueName(options['only_queue']),
            )

        def run() -> None:
            runner(touch_filename, machine, logger)

        # fork() only after we have started enough to catch failure, including
        # being able to write to our pidfile.
        if options['pidfile']:
            daemon = daemonize.Daemonize(
                app='queue_runner',
                pid=options['pidfile'],
                action=run,
            )
            daemon.start()

        else:
            # No pidfile, don't daemonize, run in foreground
            run()
