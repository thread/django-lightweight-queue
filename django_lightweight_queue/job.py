import sys
import json
import time

from .utils import get_path, get_middleware

class Job(object):
    def __init__(
        self,
        path,
        args,
        kwargs,
        timeout=None,
        sigkill_on_stop=False,
        middleware_options=None,
    ):
        self.path = path
        self.args = args
        self.kwargs = kwargs
        self.timeout = timeout
        self.sigkill_on_stop = sigkill_on_stop
        self.middleware_options = middleware_options or {}

        self._json = None

    def __repr__(self):
        return "<Job: %s(*%r, **%r)>" % (self.path, self.args, self.kwargs)

    @classmethod
    def from_json(cls, val):
        job = cls(**json.loads(val))

        # Ensures that Job.from_json(x).to_json() == x
        job._json = val

        return job

    def get_middleware_option(dotted_name, default=None):
        """
        Fetch an option on this job for middleware.

        Option names are generally expected to start with the name of the
        middleware they relate to, but it is up to the middleware in question
        to handle this.

        The name of the option should be dot separated, the dots will be used to
        separate the name of the middleware from the name of the option. At each
        level the name is used as a key into the options dict, starting with the
        middleware_options which was passed to the `task` decorator.
        """

        parts = dotted_name.split('.')
        options = self.middleware_options
        for part in parts[:-1]:
            options = options.get(part, {})

        return options.get(parts[-1], default)

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
