import os
import sys
import signal
import logging
import multiprocessing

from optparse import make_option

from django.utils.daemonize import become_daemon
from django.core.management.base import NoArgsCommand

from ... import app_settings
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

        # Ensure we can import our backend
        get_backend()

        get_middleware()
        log.info("Loaded middleware")

        # fork() only after we have started enough to catch failure, including
        # being able to write to our pidfile.
        if options['pidfile']:
            with open(options['pidfile'], 'w') as f:
                become_daemon(our_home_dir='/')
                print >>f, os.getpid()

        set_process_title("Master process")

        # Use shared state to communicate "exit after next job" to the children
        shared_state = multiprocessing.Manager().dict(running=True)

        def handle_term(signum, stack):
            log.info("Caught TERM signal")
            set_process_title("Master process exiting")
            shared_state['running'] = False
        signal.signal(signal.SIGTERM, handle_term)

        for queue, num_workers in app_settings.WORKERS.iteritems():
            for x in range(1, num_workers + 1):
                multiprocessing.Process(
                    target=worker,
                    args=(queue, x, shared_state),
                ).start()


        for x in processes:
            x.join()

        log.info("No more child processes; exiting")

def worker(queue, worker_num, shared_state):
    name = "%s/%d" % (queue, worker_num)

    log = logging.getLogger()

    log.debug("[%s] Starting", name)

    # Always reset the signal handling; we could have been restarted by the
    # master
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    # Each worker gets it own backend
    backend = get_backend()
    log.info("[%s] Loaded backend %s", name, backend)

    while shared_state['running']:
        log.debug("[%s] Checking backend for items", name)
        set_process_title(name, "Waiting for items")

        try:
            job = backend.dequeue(queue, 10)

            if job is None:
                continue

            log.debug("[%s] Running job %s", name, job)
            set_process_title(name, "Running job %s" % job)
            job.run()
        except KeyboardInterrupt:
            sys.exit(1)
