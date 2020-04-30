from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from ...types import QueueName, WorkerNumber
from ...worker import Worker


class Command(BaseCommand):
    help = "Run an individual queue worker"  # noqa:A003 # inherited name

    def add_arguments(self, parser: CommandParser) -> None:
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
            '--touch-file',
            type=str,
            dest='touch_filename',
            default=None,
            help="file to touch after jobs",
        )

    def handle(
        self,
        queue: QueueName,
        number: WorkerNumber,
        prometheus_port: int,
        touch_filename: str,
        **options: Any
    ) -> None:
        worker = Worker(
            queue=queue,
            worker_num=number,
            prometheus_port=prometheus_port,
            touch_filename=touch_filename,
        )
        worker.run()
