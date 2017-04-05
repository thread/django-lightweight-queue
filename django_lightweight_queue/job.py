import sys
import json
import time
import datetime

from .utils import get_path, get_middleware

TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

class Job(object):
    def __init__(self, path, args, kwargs, timeout=None, sigkill_on_stop=False):
        self.path = path
        self.args = args
        self.kwargs = kwargs
        self.timeout = timeout
        self.sigkill_on_stop = sigkill_on_stop
        self.created_time = datetime.datetime.utcnow()

        self._json = None

    def __repr__(self):
        return "<Job: %s(*%r, **%r) @ %s>" % (
            self.path,
            self.args,
            self.kwargs,
            self.created_time_str,
        )

    @classmethod
    def from_json(cls, val):
        as_dict = json.loads(val)

        # Historic jobs won't have a created_time, so have a default
        created_time = as_dict.pop('created_time', None)

        job = cls(**as_dict)
        if created_time is not None:
            job.created_time = datetime.datetime.strptime(
                created_time,
                TIME_FORMAT,
            )

        # Ensures that Job.from_json(x).to_json() == x
        job._json = val

        return job

    @property
    def created_time_str(self):
        return self.created_time.strftime(TIME_FORMAT)

    def run(self):
        start = time.time()

        middleware = get_middleware()

        for instance in middleware:
            if hasattr(instance, 'process_job'):
                instance.process_job(self)

        try:
            result = self.get_fn().fn(*self.args, **self.kwargs)

            time_taken = time.time() - start

            for instance in reversed(middleware):
                if hasattr(instance, 'process_result'):
                    instance.process_result(self, result, time_taken)
        except Exception:
            time_taken = time.time() - start

            exc_info = sys.exc_info()

            for instance in reversed(middleware):
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

    def as_dict(self):
        return {
            'path': self.path,
            'args': self.args,
            'kwargs': self.kwargs,
            'timeout': self.timeout,
            'sigkill_on_stop': self.sigkill_on_stop,
            'created_time': self.created_time_str,
        }

    def to_json(self):
        if self._json is None:
            self._json = json.dumps(self.as_dict())
        return self._json
