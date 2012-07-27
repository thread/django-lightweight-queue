import os
import logging

from optparse import make_option

from django.utils.daemonize import become_daemon
from django.core.management.base import NoArgsCommand

from ...utils import get_backend, get_middleware, set_process_title

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pidfile', action='store', dest='pidfile', default=None,
            help="Fork and write pidfile to this file."),
    )

    def handle_noargs(self, **options):
        level = {
            '0': logging.WARNING,
            '1': logging.INFO,
            '2': logging.DEBUG,
        }[options['verbosity']]

        set_process_title("Starting")

        logging.basicConfig(level=level, format='%(levelname).1s: %(message)s')
        logging.info("Starting queue runner")

        backend = get_backend()
        logging.info("Started backend %s", backend)

        get_middleware()
        logging.info("Loaded middleware")

        # fork() only after we have started enough to catch failure, including
        # being able to write to our pidfile.
        if options['pidfile']:
            with open(options['pidfile'], 'w') as f:
                become_daemon(our_home_dir='/')
                print >>f, os.getpid()

        while True:
            logging.debug("Checking backend for items")
            set_process_title("Waiting for items")

            try:
                job = backend.dequeue(1)
            except KeyboardInterrupt:
                return

            if job is not None:
                set_process_title("Running a job: %s" % job)
                job.run()
