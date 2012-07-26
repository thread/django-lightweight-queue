import logging

from optparse import make_option

from django.core.management.base import NoArgsCommand

from ...utils import get_backend

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

        logging.basicConfig(level=level, format='%(levelname).1s: %(message)s')
        logging.info("Starting queue runner")

        backend = get_backend()
        logging.info("Started backend %s", backend)

        while True:
            try:
                logging.debug("Checking backend for items")
                job = backend.dequeue(1)
            except KeyboardInterrupt:
                return

            if job is not None:
                job.run()
