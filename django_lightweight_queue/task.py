from .job import Job
from .utils import get_backend

from . import app_settings

class task(object):
    def __init__(self, queue='default', timeout=None, sigkill_on_stop=False):
        self.queue = queue
        self.timeout = timeout
        self.sigkill_on_stop = sigkill_on_stop

        app_settings.WORKERS.setdefault(self.queue, 1)

    def __call__(self, fn):
        return TaskWrapper(fn, self.queue, self.timeout, self.sigkill_on_stop)

class TaskWrapper(object):
    def __init__(self, fn, queue, timeout, sigkill_on_stop):
        self.fn = fn
        self.queue = queue
        self.timeout = timeout
        self.sigkill_on_stop = sigkill_on_stop

        self.path = '%s.%s' % (fn.__module__, fn.__name__)

    def __repr__(self):
        return "<TaskWrapper: %s>" % self.path

    def __call__(self, *args, **kwargs):
        # Allow us to override which queue at the last moment
        queue = kwargs.pop('queue', self.queue)

        job = Job(self.path, args, kwargs, self.timeout, self.sigkill_on_stop)
        job.validate()

        get_backend().enqueue(job, queue)
