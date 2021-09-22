import time

from ..job import Job
from .base import BaseBackend
from ..types import QueueName, WorkerNumber


class SynchronousBackend(BaseBackend):
    """
    This backend has at-most-once semantics.
    """

    def enqueue(self, job: Job, queue: QueueName) -> None:
        job.run(queue=queue, worker_num=WorkerNumber(0))

    def dequeue(self, queue: QueueName, worker_num: WorkerNumber, timeout: float) -> None:
        # Cannot dequeue from the synchronous backend but we can emulate by
        # never returning anything
        time.sleep(timeout)

    def length(self, queue: QueueName) -> int:
        # The length is the number of items waiting to be processed, which can
        # be defined as always 0 for the synchronous backend
        return 0
