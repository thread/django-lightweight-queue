import time

class SynchronousBackend(object):
    """
    This backend has at-most-once semantics.
    """
    def startup(self, queue):
        pass

    def enqueue(self, job, queue):
        job.run()

    def dequeue(self, queue, worker_num, timeout):
        # Cannot dequeue from the synchronous backend but we can emulate by
        # never returning anything
        time.sleep(timeout)

    def length(self, queue):
        # The length is the number of items waiting to be processed, which can
        # be defined as always 0 for the synchronous backend
        return 0

    def processed_job(self, queue, worker_num, job):
        pass
