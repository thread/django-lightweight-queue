import sys
import time

from django.utils import simplejson

from .utils import get_path, get_middleware

class Job(object):
    def __init__(self, path, args, kwargs):
        self.path = path
        self.args = args
        self.kwargs = kwargs

    def run(self):
        start = time.time()

        middleware = get_middleware()

        for instance in middleware:
            if hasattr(instance, 'process_job'):
                instance.process_job(self)

        try:
            result = self.get_fn().fn(*self.args, **self.kwargs)

            time_taken = time.time() - start

            for instance in middleware:
                if hasattr(instance, 'process_result'):
                    instance.process_result(self, result, time_taken)
        except Exception, exc:
            time_taken = time.time() - start

            exc_info = sys.exc_info()

            for instance in middleware:
                if hasattr(instance, 'process_exception'):
                    instance.process_exception(self, time_taken, *exc_info)

    def validate(self):
        # Ensure these execute without exception so that we cannot enqueue
        # things that are impossible to dequeue.
        self.get_fn()
        self.to_json()

    def get_fn(self):
        return get_path(self.path)

    def to_json(self):
        return simplejson.dumps({
            'args': self.args,
            'kwargs': self.kwargs,
        })
