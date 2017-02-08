import os
import sys
import time
import signal
import logging
import datetime
import itertools
import multiprocessing

from prometheus_client import start_http_server, Summary

from django.db import connections, transaction

from . import app_settings
from .utils import get_backend, set_process_title, configure_logging

if app_settings.ENABLE_PROMETHEUS:
    job_duration = Summary(
        'item_processed_seconds',
        "Item processing time",
        ['queue'],
    )

class Worker(multiprocessing.Process):
    def __init__(self, queue, worker_index, worker_num, back_channel, running, log_level, log_filename, touch_filename):
        self.queue = queue
        self.worker_index = worker_index
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

        if app_settings.ENABLE_PROMETHEUS:
            metrics_port = app_settings.PROMETHEUS_START_PORT + self.worker_index
            self.log.info("Exporting metrics on port %d" % metrics_port)
            start_http_server(metrics_port)

        self.log.debug("Starting")

        # Always reset the signal handling; we could have been restarted by the
        # master
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

        # Each worker gets it own backend
        backend = get_backend(self.queue)
        self.log.info("Loaded backend %s", backend)

        time_item_last_processed = datetime.datetime.utcnow()

        for item_count in itertools.count():
            if not self.running.value:
                break

            if self.idle_time_reached(time_item_last_processed):
                self.log.info("Exiting due to reaching idle time limit")
                break

            if item_count > 1000:
                self.log.info("Exiting due to reaching item limit")
                break

            try:
                pre_process_time = time.time()
                item_processed = self.process(backend)
                post_process_time = time.time()

                if app_settings.ENABLE_PROMETHEUS:
                    job_duration.observe(
                        post_process_time - pre_process_time,
                        self.queue,
                    )

                if item_processed:
                    time_item_last_processed = datetime.datetime.utcnow()

            except KeyboardInterrupt:
                sys.exit(1)

        self.log.info("Exiting")

    def idle_time_reached(self, time_item_last_processed):
        idle_time = datetime.datetime.utcnow() - time_item_last_processed

        return idle_time > datetime.timedelta(minutes=30)

    def process(self, backend):
        self.log.debug("Checking backend for items")
        self.set_process_title("Waiting for items")

        # Tell master process that we are not processing anything.
        self.tell_master(None, False)

        job = backend.dequeue(self.queue, self.worker_num, 15)
        if job is None:
            return False

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

        backend.processed_job(self.queue, self.worker_num, job)

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

        return True

    def tell_master(self, timeout, sigkill_on_stop):
        self.back_channel.put((
            self.queue,
            self.worker_num,
            timeout,
            sigkill_on_stop,
        ))

    def set_process_title(self, *titles):
        set_process_title(self.name, *titles)
