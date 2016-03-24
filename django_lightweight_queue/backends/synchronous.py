import time

class SynchronousBackend(object):
    def enqueue(self, job, queue):
        job.run()

    def dequeue(self, queue, timeout):
        # Cannot dequeue from the synchronous backend but we can emulate by
        # never returning anything
        time.sleep(timeout)

    def length(self, queue):
        # The length is the number of items waiting to be processed, which can
        # be defined as always 0 for the synchronous backend
        return 0
