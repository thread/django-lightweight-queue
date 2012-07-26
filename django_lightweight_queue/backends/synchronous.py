import time

from django.utils import simplejson

from ..utils import get_path

class SynchronousBackend(object):
    def enqueue(self, job):
        job.run()

    def dequeue(self, timeout):
        # Cannot dequeue from the synchronous backend but we can emulate by
        # never returning anything
        time.sleep(timeout)
