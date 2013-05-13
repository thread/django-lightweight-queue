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

        # Start workers
        for queue, num_workers in app_settings.WORKERS.iteritems():
            for x in range(1, num_workers + 1):
                Worker(
                    queue,
                    x,
                    back_channel,
                    running,
                    level,
                    log_filename('%s.%s' % (queue, x)),
                ).start()

        children = {}

        while running.value:
            time.sleep(1)

            try:
                log.debug("Checking back channel for items")

                # We don't use the timeout kwarg so that when we get a TERM
                # signal we don't have problems with interrupted system calls.
                pid, queue, worker_num, kill_after = back_channel.get_nowait()

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
                Worker(
                    queue,
                    worker_num,
                    back_channel,
                    running,
                    level,
                    log_filename('%s.%s' % (queue, worker_num)),
                ).start()

        log.info("Exiting")

class Worker(multiprocessing.Process):
    def __init__(self, queue, worker_num, back_channel, running, log_level, log_filename):
        self.queue = queue
        self.worker_num = worker_num

        self.back_channel = back_channel
        self.running = running

        self.log_level = log_level
        self.log_filename = log_filename

        # Logfiles must be opened in child process
        self.log = None

        super(Worker, self).__init__()

        # Setup @property.setter on Process
        self.name = '%s/%s' % (queue, worker_num)

    def run(self):
        self.log = logging.getLogger()
        for x in self.log.handlers:
            self.log.removeHandler(x)

        logging.basicConfig(
            level=self.log_level,
            format='%%(asctime)-15s %%(process)d %(queue)s/%(worker_num)d '
                    '%%(levelname).1s: %%(message)s' % {
                'queue': self.queue,
                'worker_num': self.worker_num,
            },
            filename=self.log_filename,
        )

        self.log.debug("Starting")

        # Always reset the signal handling; we could have been restarted by the
        # master
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

        # Each worker gets it own backend
        backend = get_backend()
        self.log.info("Loaded backend %s", backend)

        while self.running.value:
            try:
                self.process(backend)
            except KeyboardInterrupt:
                sys.exit(1)

        self.log.info("Exiting")

    def process(self, backend):
        self.log.debug("Checking backend for items")
        self.set_process_title("Waiting for items")

        # Tell master process that we are not processing anything.
        self.tell_master(None)

        job = backend.dequeue(self.queue, 1)
        if job is None:
            return

        timeout = job.get_fn().timeout

        # Tell master process if/when it should kill this child
        if timeout is not None:
            after = time.time() + timeout
            self.log.debug("Should be killed after %s", after)
            self.tell_master(after)

        self.log.debug("Running job %s", job)
        self.set_process_title("Running job %s" % job)
        job.run()

    def tell_master(self, value):
        self.back_channel.put((os.getpid(), self.queue, self.worker_num, value))

    def set_process_title(self, *titles):
        set_process_title(
            '%s/%d' % (self.queue, self.worker_num),
            *titles
        )
