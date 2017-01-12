import re
import sys
import imp
import time
import logging
import datetime
import multiprocessing

from django.apps import apps
from django.core.management import call_command

from . import app_settings
from .task import task
from .utils import set_process_title, get_backend, configure_logging

CRON_QUEUE_NAME = 'cron_scheduler'


class CronScheduler(multiprocessing.Process):
    def __init__(self, running, log_level, log_filename, config):
        self.running = running
        self.log_level = log_level
        self.log_filename = log_filename
        self.config = config

        # Logfiles must be opened in child process
        self.log = None

        super(CronScheduler, self).__init__()

    def run(self):
        set_process_title("Cron scheduler process")

        self.log = logging.getLogger()
        for x in self.log.handlers:
            self.log.removeHandler(x)

        configure_logging(
            level=self.log_level,
            format='%%(asctime)-15s %%(process)d %s %%(levelname).1s: '
                '%%(message)s' % (CRON_QUEUE_NAME,),
            filename=self.log_filename,
        )

        self.log.debug("Starting")

        backend = get_backend(CRON_QUEUE_NAME)
        self.log.info("Loaded backend %s", backend)

        while self.running.value:
            try:
                self.tick(backend)

                # Sleep until the next second boundary. This corrects for skew
                # caused by the accumulation of tick() runtime.
                time.sleep((1 - time.time() % 1))
            except KeyboardInterrupt:
                sys.exit(1)

        self.log.info("Exiting")

    def tick(self, backend):
        self.log.debug("tick()")

        t = datetime.datetime.utcnow()

        # Run once per minute
        if t.second != 0:
            return

        for row in self.config:
            if not (
                row['hour_matcher'](t.hour) and
                row['min_matcher'](t.minute) and
                row['day_matcher'](t.isoweekday())
            ):
                continue

            self.log.info("Enqueueing %s", row['command'])

            execute(
                row['command'],
                django_lightweight_queue_queue=row['queue'],
                django_lightweight_queue_timeout=row['timeout'],
                django_lightweight_queue_sigkill_on_stop=row['sigkill_on_stop'],
                *row.get('command_args', []),
                **row.get('command_kwargs', {})
            )

            self.log.debug("Enqueued %s", row)


def get_cron_config():
    config = []

    def get_matcher(minval, maxval, t):
        if t == '*':
            return lambda x: True
        parts = re.split(r'\s*,\s*', t)
        if not parts:
            return
        t_parts = [int(x) for x in parts]
        for num in t_parts:
            assert num >= minval and num <= maxval, \
                "Invalid time specified in cron config. " \
                "Specified: %s, minval: %s, maxval: %s" % (
                    num,
                    minval,
                    maxval,
                )
        return lambda x: x in t_parts

    for app_config in apps.get_app_configs():
        app = app_config.name
        try:
            # __import__ will break with anything other than a str object(!),
            # including e.g. unicode. So force to a str.
            part = str(app.split('.')[-1])

            app_path = __import__(app, {}, {}, [part]).__path__
        except AttributeError:
            continue

        try:
            imp.find_module('cron', app_path)
        except ImportError:
            continue

        mod = __import__('%s.cron' % app, fromlist=(app,))

        for row in mod.CONFIG:
            row['min_matcher'] = get_matcher(0, 59, row.get('minutes'))
            row['hour_matcher'] = get_matcher(0, 23, row.get('hours'))
            row['day_matcher'] = get_matcher(1,  7, row.get('days', '*'))
            row['queue'] = row.get('queue', 'cron')
            row['timeout'] = row.get('timeout', None)
            row['sigkill_on_stop'] = row.get('sigkill_on_stop', False)
            config.append(row)

    return config


def ensure_queue_workers_for_config(config):
    """
    Modify the ``WORKERS`` setting such that each of the queues in the given
    cron configuration have some queue workers specified.

    Queues explicitly configured will not be changed, so it is possible that
    a queue mentioned in the cron configuration will actually (still) have no
    workers after this function is run.
    """
    for row in config:
        app_settings.WORKERS.setdefault(row['queue'], 1)


@task()
def execute(name, *args, **kwargs):
    call_command(name, *args, **kwargs)
