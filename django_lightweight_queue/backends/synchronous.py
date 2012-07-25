from django.utils import simplejson

from ..utils import get_path

class SynchronousBackend(object):
    def enqueue(self, job):
        job.run()
