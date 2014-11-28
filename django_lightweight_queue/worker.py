import os
import sys
import signal
import logging
import multiprocessing

from django.db import connections, transaction

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

        # Defaults for values dynamically updated by the master process when
        # running a job
        self.kill_after = None
        self.sigkill_on_stop = False

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
        self.tell_master(None, False)

        job = backend.dequeue(self.queue, 1)
        if job is None:
            return

        # Update master what we are doing
        self.tell_master(
            job.timeout,
            job.sigkill_on_stop,
        )

        self.log.debug("Running job %s", job)
        self.set_process_title("Running job %s" % job)

        if job.run() and self.touch_filename:
            with open(self.touch_filename, 'a'):
                os.utime(self.touch_filename, None)

        # Emulate Django's request_finished signal and close all of our
        # connections. Django assumes that making a DB connection is cheap, so
        # it's probably safe to assume that too.
        for x in connections:
            try:
                # Removed in recent versions
                transaction.abort(x)
            except AttributeError:
                pass
            connections[x].close()

    def tell_master(self, timeout, sigkill_on_stop):
        self.back_channel.put((
            self.queue,
            self.worker_num,
            timeout,
            sigkill_on_stop,
        ))

    def set_process_title(self, *titles):
        set_process_title(self.name, *titles)
