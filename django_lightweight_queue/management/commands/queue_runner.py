import os
import logging
import optparse

from django.db import models
from django.utils.daemonize import become_daemon
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
    )

    def handle_noargs(self, **options):
        level = {
            '0': logging.WARNING,
            '1': logging.INFO,
            '2': logging.DEBUG,
        }[options['verbosity']]

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

        configure_logging(
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
        models.get_models()
        log.info("Loaded models")

        # fork() only after we have started enough to catch failure, including
        # being able to write to our pidfile.
        if options['pidfile']:
            with open(options['pidfile'], 'w') as f:
                become_daemon(our_home_dir='/')
                print >>f, os.getpid()

        runner(log, log_filename, touch_filename)
