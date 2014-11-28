import sys
import json
import time

from .utils import get_path, get_middleware

class Job(object):
    def __init__(self, path, args, kwargs, timeout=None, sigkill_on_stop=False):
        self.path = path
        self.args = args
        self.kwargs = kwargs
        self.timeout = timeout
        self.sigkill_on_stop = sigkill_on_stop

        self._json = None

    def __repr__(self):
        return "<Job: %s(*%r, **%r)>" % (self.path, self.args, self.kwargs)

    @classmethod
    def from_json(cls, val):
        return cls(**json.loads(val))

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
        except Exception:
            time_taken = time.time() - start

            exc_info = sys.exc_info()

            for instance in middleware:
                if hasattr(instance, 'process_exception'):
                    try:
                        instance.process_exception(self, time_taken, *exc_info)
                    except Exception:
                        pass

            return False

        return True

    def validate(self):
        # Ensure these execute without exception so that we cannot enqueue
        # things that are impossible to dequeue.
        self.get_fn()
        self.to_json()

    def get_fn(self):
        return get_path(self.path)

    def to_json(self):
        if self._json is None:
            self._json = json.dumps({
                'path': self.path,
                'args': self.args,
                'kwargs': self.kwargs,
                'timeout': self.timeout,
                'sigkill_on_stop': self.sigkill_on_stop,
            })
        return self._json
