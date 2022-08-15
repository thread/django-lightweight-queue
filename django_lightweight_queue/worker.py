import os
import sys
import math
import time
import signal
import logging
import datetime
import itertools
from typing import Optional

from prometheus_client import Summary, start_http_server

from django.db import connections, transaction

from . import app_settings
from .types import QueueName, WorkerNumber
from .utils import get_logger, get_backend, set_process_title
from .backends.base import BaseBackend

if app_settings.ENABLE_PROMETHEUS:
    job_duration = Summary(
        'item_processed_seconds',
        "Item processing time",
        ['queue'],
    )


class Worker:
    def __init__(
        self,
        queue: QueueName,
        prometheus_port: int,
        worker_num: WorkerNumber,
        touch_filename: str,
    ) -> None:
        self.queue = queue
        self.prometheus_port = prometheus_port
        self.worker_num = worker_num

        self.running = True

        self.touch_filename = touch_filename

        self.logger = get_logger('dlq.worker')

        # Defaults for values dynamically updated by the master process when
        # running a job
        self.kill_after = None
        self.sigkill_on_stop = False

        super().__init__()

        # Setup @property.setter on Process
        self.name = '{}/{}'.format(queue, worker_num)

    def run(self) -> None:
        if app_settings.ENABLE_PROMETHEUS and self.prometheus_port is not None:
            self.log(logging.INFO, "Exporting metrics on port {}".format(self.prometheus_port))
            start_http_server(self.prometheus_port)

        # Always reset the signal handling; we could have been restarted by the
        # master
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)

        # Each worker gets it own backend
        backend = get_backend(self.queue)
        self.log(logging.DEBUG, "Loaded backend {}".format(backend))

        time_item_last_processed = datetime.datetime.utcnow()

        self.log(logging.DEBUG, "Worker started")

        for item_count in itertools.count():
            if not self.running:
                break

            if self.idle_time_reached(time_item_last_processed):
                self.log(logging.INFO, "Exiting due to reaching idle time limit")
                break

            if item_count > 1000:
                self.log(logging.INFO, "Exiting due to reaching item limit")
                break

            try:
                pre_process_time = time.time()
                item_processed = self.process(backend)
                post_process_time = time.time()

                if app_settings.ENABLE_PROMETHEUS:
                    job_duration.labels(self.queue).observe(
                        post_process_time - pre_process_time,
                    )

                if item_processed:
                    time_item_last_processed = datetime.datetime.utcnow()

            except KeyboardInterrupt:
                sys.exit(1)

        self.log(logging.DEBUG, "Exiting")

    def _handle_sigusr2(self, signum: int, frame: object) -> None:
        self.running = False

    def idle_time_reached(self, time_item_last_processed: datetime.datetime) -> bool:
        idle_time = datetime.datetime.utcnow() - time_item_last_processed

        return idle_time > datetime.timedelta(minutes=30)

    def process(self, backend: BaseBackend) -> bool:
        self.log(logging.DEBUG, "Checking backend for items")

        self.set_process_title("Waiting for items")

        self.configure_cancellation(timeout=None, sigkill_on_stop=True)

        job = backend.dequeue(self.queue, self.worker_num, 15)
        if job is None:
            return False

        # Update master what we are doing
        self.configure_cancellation(
            timeout=job.timeout,
            sigkill_on_stop=job.sigkill_on_stop,
        )

        self.set_process_title("Running job {}".format(job))

        if job.run(queue=self.queue, worker_num=self.worker_num) and self.touch_filename:
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

    def configure_cancellation(self, timeout: Optional[int], sigkill_on_stop: bool) -> None:
        if sigkill_on_stop:
            # SIGUSR2 can be taken to just cause the process to die
            # immediately. This is the default action for SIGUSR2.
            # Reference: signal(7)
            signal.signal(signal.SIGUSR2, signal.SIG_DFL)
        else:
            # SIGUSR2 indicates we should shut down after handling the
            # next entry.
            signal.signal(signal.SIGUSR2, self._handle_sigusr2)

        if timeout is not None:
            signal.signal(signal.SIGALRM, self._handle_alarm)
            # alarm(3) takes whole seconds
            alarm_duration = int(math.ceil(timeout))
            signal.alarm(alarm_duration)
        else:
            # Cancel any scheduled alarms
            signal.alarm(0)

    def _handle_alarm(self, signal_number: int, frame: object) -> None:
        # Log for observability
        self.log(logging.ERROR, "Alarm received: job has timed out")

        # Disconnect ourselves then re-signal so that Python does what it
        # normally would. We could raise an exception here, however raising
        # exceptions from signal handlers is generally discouraged.
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        # TODO(python-upgrade): use signal.raise_signal on Python 3.8+
        os.kill(os.getpid(), signal.SIGALRM)

    def set_process_title(self, *titles: str) -> None:
        set_process_title(self.name, *titles)

    def log(self, level: int, message: str) -> None:
        self.logger.log(level, message, extra={
            'queue': self.queue,
            'worker': self.worker_num,
        })
