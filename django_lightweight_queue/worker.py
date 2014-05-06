import os
import sys
import time
import signal
import logging
import multiprocessing

from .utils import get_backend, set_process_title, configure_logging

class Worker(multiprocessing.Process):
    def __init__(self, queue, worker_num, back_channel, running, log_level, log_filename, touch_filename):
        self.queue = queue
        self.worker_num = worker_num

        self.back_channel = back_channel
        self.running = running

        self.log_level = log_level
        self.log_filename = log_filename
        self.touch_filename = touch_filename

        # Logfiles must be opened in child process
        self.log = None

        # Used by the parent
        self.kill_after = None

        super(Worker, self).__init__()

        # Setup @property.setter on Process
        self.name = '%s/%s' % (queue, worker_num)

    def run(self):
        self.log = logging.getLogger()
        for x in self.log.handlers:
            self.log.removeHandler(x)

        configure_logging(
            level=self.log_level,
            format='%%(asctime)-15s %%(process)d %s %%(levelname).1s: '
                '%%(message)s' % self.name,
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

        if job.run() and self.touch_filename:
            with open(self.touch_filename, 'a'):
                os.utime(self.touch_filename, None)

    def tell_master(self, value):
        self.back_channel.put((self.queue, self.worker_num, value))

    def set_process_title(self, *titles):
        set_process_title(self.name, *titles)
