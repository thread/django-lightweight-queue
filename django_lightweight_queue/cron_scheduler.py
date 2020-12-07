import re
import imp
import time
import datetime
import threading

from django.apps import apps
from django.core.management import call_command

from .task import task
from .utils import get_logger, get_backend, contribute_implied_queue_name

CRON_QUEUE_NAME = 'cron_scheduler'


class CronScheduler(threading.Thread):
    def __init__(self, config):
        self.config = config
        self.logger = get_logger('dlq.cron')
        super(CronScheduler, self).__init__(daemon=True)

    def run(self):
        self.logger.debug("Starting cron thread")

        backend = get_backend(CRON_QUEUE_NAME)
        self.logger.info(
            "Loaded backend {}".format(backend),
            extra={'backend': backend},
        )

        while True:
            # This will run until the process terminates.
            self.tick(backend)

            # Sleep until the next second boundary. This corrects for skew
            # caused by the accumulation of tick() runtime.
            time.sleep((1 - time.time() % 1))

    def tick(self, backend):
        self.logger.debug(
            "Cron thread checking for work",
            extra={'backend': backend},
        )

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

            self.logger.debug(
                "Enqueueing {}".format(row['command']),
                extra={
                    'target_queue': row['queue'],
                    'command': row['command'],
                },
            )

            execute(
                row['command'],
                django_lightweight_queue_queue=row['queue'],
                django_lightweight_queue_timeout=row['timeout'],
                django_lightweight_queue_sigkill_on_stop=row['sigkill_on_stop'],
                *row.get('command_args', []),
                **row.get('command_kwargs', {}),
            )

            self.logger.info(
                "Enqueued {}".format(row['command']),
                extra={
                    'target_queue': row['queue'],
                    'command': row['command'],
                },
            )


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
            assert num >= minval and num <= maxval, (
                "Invalid time specified in cron config. "
                "Specified: {}, minval: {}, maxval: {}".format(
                    num,
                    minval,
                    maxval,
                )
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

        mod = __import__('{}.cron'.format(app), fromlist=(app,))

        for row in mod.CONFIG:
            row['min_matcher'] = get_matcher(0, 59, row.get('minutes'))
            row['hour_matcher'] = get_matcher(0, 23, row.get('hours'))
            row['day_matcher'] = get_matcher(1, 7, row.get('days', '*'))
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
        contribute_implied_queue_name(row['queue'])


@task()
def execute(name, *args, **kwargs):
    call_command(name, *args, **kwargs)
