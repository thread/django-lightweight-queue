import os
import sys
import signal
import logging

from optparse import make_option

from django.utils.daemonize import become_daemon
from django.core.management.base import NoArgsCommand

from ...utils import get_backend, get_middleware, set_process_title

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pidfile', action='store', dest='pidfile', default=None,
            help="Fork and write pidfile to this file."),
        make_option('--logfile', action='store', dest='logfile', default=None,
            help="Log to the specified file."),
    )

    def handle_noargs(self, **options):
        level = {
            '0': logging.WARNING,
            '1': logging.INFO,
            '2': logging.DEBUG,
        }[options['verbosity']]

        set_process_title("Starting")

        logging.basicConfig(
            level=level,
            format='%(asctime)-15s %(process)d %(levelname).1s: %(message)s',
            filename=options['logfile'],
        )

        log = logging.getLogger()

        log.info("Starting queue runner")

        self.backend = get_backend()
        log.info("Started backend %s", self.backend)

        get_middleware()
        log.info("Loaded middleware")

        # fork() only after we have started enough to catch failure, including
        # being able to write to our pidfile.
        if options['pidfile']:
            with open(options['pidfile'], 'w') as f:
                become_daemon(our_home_dir='/')
                print >>f, os.getpid()

        self.should_run = True
        def handle_term(signum, stack):
            logging.info("Caught TERM signal; exiting")
            self.should_run = False
        signal.signal(signal.SIGTERM, handle_term)

        while self.should_run:
            logging.debug("Checking backend for items")
            set_process_title("Waiting for items")

            try:
                job = backend.dequeue(1)

                if job is not None:
                    set_process_title("Running a job: %s" % job)
                    job.run()
            except KeyboardInterrupt:
                sys.exit(1)
