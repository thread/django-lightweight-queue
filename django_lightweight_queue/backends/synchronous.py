import time

from django.utils import simplejson

from ..utils import get_path

class SynchronousBackend(object):
    def enqueue(self, job):
        job.run()

    def dequeue(self):
        # Cannot dequeue from the synchronous backend but we can emulate
        while True:
            time.sleep(60)
