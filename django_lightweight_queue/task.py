from .job import Job
from .utils import get_backend

from . import app_settings

class task(object):
    def __init__(self, *args, **kwargs):
        self.queue = kwargs.pop('queue', 'default')
        app_settings.WORKERS.setdefault(self.queue, 1)

        self.args = args
        self.kwargs = kwargs

    def __call__(self, fn):
        return TaskWrapper(fn, self.queue, *self.args, **self.kwargs)

class TaskWrapper(object):
    def __init__(self, fn, queue, *args, **kwargs):
        self.fn = fn
        self.queue = queue
        self.path = '%s.%s' % (fn.__module__, fn.__name__)

    def __repr__(self):
        return "<TaskWrapper: %s>" % self.path

    def __call__(self, *args, **kwargs):
        job = Job(self.path, args, kwargs)
        job.validate()

        get_backend().enqueue(job, self.queue)
