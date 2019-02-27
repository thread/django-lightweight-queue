import sys
import logging
import argparse

from django.core.management.base import BaseCommand

from ...worker import Worker


class Command(BaseCommand):
    help = "Run an individual queue worker"

    def add_arguments(self, parser):
        parser.add_argument(
            'queue',
            help="queue for which this is a worker",
        )
        parser.add_argument(
            'number',
            type=int,
            help="worker number within this queue",
        )
        parser.add_argument(
            '--prometheus-port',
            type=int,
            help="port number on which to run Prometheus",
        )
        parser.add_argument(
            '--log-level',
            choices=[x.lower() for x in logging._nameToLevel.keys()],
            default='warning',
            help="log level to set",
        )
        parser.add_argument(
            '--log-file',
            type=str,
            dest='log_filename',
            help="log destination",
        )
        parser.add_argument(
            '--touch-file',
            type=str,
            dest='touch_filename',
            default=None,
            help="file to touch after jobs",
        )

    def handle(
        self,
        queue,
        number,
        prometheus_port,
        log_level,
        log_filename,
        touch_filename,
        **options
    ):
        worker = Worker(
            queue=queue,
            worker_num=number,
            prometheus_port=prometheus_port,
            log_level=logging._nameToLevel[log_level.upper()],
            log_filename=log_filename,
            touch_filename=touch_filename,
        )
        worker.run()
