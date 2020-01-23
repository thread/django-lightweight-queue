import time

from .base import BaseBackend


class SynchronousBackend(BaseBackend):
    """
    This backend has at-most-once semantics.
    """

    def enqueue(self, job, queue):
        job.run(queue=queue, worker_num=0)

    def dequeue(self, queue, worker_num, timeout):
        # Cannot dequeue from the synchronous backend but we can emulate by
        # never returning anything
        time.sleep(timeout)

    def length(self, queue):
        # The length is the number of items waiting to be processed, which can
        # be defined as always 0 for the synchronous backend
        return 0
