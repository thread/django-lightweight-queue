import os
import sys
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

        # Set the title now - multiprocessing will create an extra process
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

        # Start workers
        for queue, num_workers in app_settings.WORKERS.iteritems():
            for x in range(1, num_workers + 1):
                multiprocessing.Process(
                    target=worker,
                    args=(queue, x, back_channel, running),
                ).start()

        children = {}
        while running.value:
            try:
                log.debug("Checking back channel for items")
                pid, queue, worker_num, kill_after = back_channel.get(timeout=1)

                # A child is telling us if/when they should be killed
                children.pop('pid', None)
                if kill_after is not None:
                    children[pid] = (queue, worker_num, kill_after)
            except Empty:
                pass

            # Check if any children need killing
            for pid, (queue, worker_num, kill_after) in children.items():
                if time.time() < kill_after:
                    continue

                log.warning("Killing PID %d due to timeout", pid)
                children.pop(pid, None)
                os.kill(pid, signal.SIGKILL)

                log.info("Starting replacement %s/%d worker", queue, worker_num)
                multiprocessing.Process(
                    target=worker,
                    args=(queue, worker_num, back_channel, running),
                ).start()

        log.info("Exiting")

def worker(queue, worker_num, back_channel, running):
    name = "%s/%d" % (queue, worker_num)

    log = logging.getLogger()

    log.debug("[%s] Starting", name)

    # Always reset the signal handling; we could have been restarted by the
    # master
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    # Each worker gets it own backend
    backend = get_backend()
    log.info("[%s] Loaded backend %s", name, backend)

    while running.value:
        log.debug("[%s] Checking backend for items", name)
        set_process_title(name, "Waiting for items")

        # Tell master process that we are not doing anything anymore
        back_channel.put((os.getpid(), queue, worker_num, None))

        try:
            job = backend.dequeue(queue, 1)
            if job is None:
                continue

            timeout = job.get_fn().timeout

            # Tell master process if/when it should kill this child
            if timeout is not None:
                after = time.time() + timeout
                log.debug(
                    "[%s] Informing master I should be killed >%s", name, after,
                )
                back_channel.put((os.getpid(), queue, worker_num, after))

            log.debug("[%s] Running job %s", name, job)
            set_process_title(name, "Running job %s" % job)
            job.run()
        except KeyboardInterrupt:
            sys.exit(1)

    log.info("[%s] Exiting", name)
