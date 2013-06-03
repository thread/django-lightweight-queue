import os
import time
import signal
import logging
import multiprocessing

from Queue import Empty
from optparse import make_option

from django.utils.daemonize import become_daemon
from django.core.management.base import NoArgsCommand

from ... import app_settings
from ...utils import get_backend, get_middleware, set_process_title
from ...worker import Worker

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

        def log_filename(name):
            try:
                return options['logfile'] % name
            except TypeError:
                return options['logfile']

        logging.basicConfig(
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

        # fork() only after we have started enough to catch failure, including
        # being able to write to our pidfile.
        if options['pidfile']:
            with open(options['pidfile'], 'w') as f:
                become_daemon(our_home_dir='/')
                print >>f, os.getpid()

        # Set a dummy title now; multiprocessing will create an extra process
        # which will inherit it - we'll set the real title afterwards
        set_process_title("Internal master process")

        # Use a multiprocessing.Queue to communicate back to the master if/when
        # children should be killed.
        back_channel = multiprocessing.Queue()

        # Use shared state to communicate "exit after next job" to the children
        running = multiprocessing.Value('d', 1)

        set_process_title("Master process")

        def handle_term(signum, stack):
            log.info("Caught TERM signal")
            set_process_title("Master process exiting")
            running.value = 0
        signal.signal(signal.SIGTERM, handle_term)

        workers = {}
        for queue, num_workers in app_settings.WORKERS.iteritems():
            for x in range(1, num_workers + 1):
                workers[(queue, x)] = None

        while running.value:
            for (queue, worker_num), worker in workers.items():

                # Kill any workers that have exceeded their timeout
                if worker and worker.kill_after and time.time() > worker.kill_after:
                    log.warning("Killing %s due to timeout", worker.name)

                    try:
                        os.kill(worker.pid, signal.SIGKILL)

                        # Sleep for a bit so we don't start workers constantly
                        time.sleep(0.1)
                    except OSError:
                        pass

                # Ensure that all workers are now running (idempotent)
                if worker is None or not worker.is_alive():
                    if worker is None:
                        log.info("Starting worker #%d for %s", worker_num, queue)
                    else:
                        log.info(
                            "Starting missing worker %s (exit code was: %s)",
                            worker.name,
                            worker.exitcode,
                        )

                    worker = Worker(
                        queue,
                        worker_num,
                        back_channel,
                        running,
                        level,
                        log_filename('%s.%s' % (queue, worker_num)),
                    )

                    workers[(queue, worker_num)] = worker
                    worker.start()

            while True:
                try:
                    log.debug("Checking back channel for items")

                    # We don't use the timeout kwarg so that when we get a TERM
                    # signal we don't have problems with interrupted system calls.
                    queue, worker_num, kill_after = back_channel.get_nowait()
                except Empty:
                    break

                worker = workers[(queue, worker_num)]
                log.debug(
                    "Setting kill_after for %s to %r", worker.name, kill_after,
                )
                worker.kill_after = kill_after

            time.sleep(1)

        log.info("Exiting")
