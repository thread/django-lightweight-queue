import logging
import optparse
import daemonize

from django.apps import apps
from django.core.management.base import NoArgsCommand

from ...utils import get_backend, get_middleware, configure_logging
from ...runner import runner

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        optparse.make_option('--pidfile', action='store', dest='pidfile', default=None,
            help="Fork and write pidfile to this file."),
        optparse.make_option('--logfile', action='store', dest='logfile', default=None,
            help="Log to the specified file."),
        optparse.make_option('--touchfile', action='store', dest='touchfile', default=None,
            help="touch(1) the specified file after running a job."),
        optparse.make_option('--machine', action='store', dest='machine_number', default='1',
            help="Machine number, for parallelism"),
        optparse.make_option('--of', action='store', dest='machine_count', default='1',
            help="Total number of machines running the queues"),
    )

    def handle_noargs(self, **options):
        # Django < 1.8.3 leaves options['verbosity'] as a string so we cast to
        # ensure an int.
        verbosity = int(options['verbosity'])

        level = {
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG,
        }[verbosity]

        def log_filename(name):
            try:
                return options['logfile'] % name
            except TypeError:
                return options['logfile']

        def touch_filename(name):
            try:
                return options['touchfile'] % name
            except TypeError:
                return None

        log_fd = configure_logging(
            level=level,
            format='%(asctime)-15s %(process)d %(levelname).1s: %(message)s',
            filename=log_filename('master'),
        )

        log = logging.getLogger()

        log.info("Starting queue runner")

        # Ensure children will be able to import our backend
        get_backend()

        get_middleware()
        log.info("Loaded middleware")

        # Ensure children will be able to import most things, but also try and
        # save memory by importing as much as possible before the fork() as it
        # has copy-on-write semantics.
        apps.get_models()
        log.info("Loaded models")

        def run():
            runner(
                log,
                log_filename,
                touch_filename,
                machine_number=int(options['machine_number']),
                machine_count=int(options['machine_count']),
            )

        # fork() only after we have started enough to catch failure, including
        # being able to write to our pidfile.
        if options['pidfile']:
            daemon = daemonize.Daemonize(
                app='queue_runner',
                pid=options['pidfile'],
                action=run,
                keep_fds=[log_fd],
            )
            daemon.start()

        else:
            # No pidfile, don't daemonize, run in foreground
            run()
