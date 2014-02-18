import time

class SynchronousBackend(object):
    def enqueue(self, job, queue):
        job.run()

    def dequeue(self, queue, timeout):
        # Cannot dequeue from the synchronous backend but we can emulate by
        # never returning anything
        time.sleep(timeout)
