from .job import Job
from .utils import get_backend

TASKS = {}

class task(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, fn):
        return TaskWrapper(fn, *self.args, **self.kwargs)

class TaskWrapper(object):
    def __init__(self, fn, *args, **kwargs):
        self.fn = fn
        self.path = '%s.%s' % (fn.__module__, fn.__name__)

        TASKS[self.path] = self

    def __repr__(self):
        return "<TaskWrapper: %s>" % self.path

    def __call__(self, *args, **kwargs):
        job = Job(self.path, args, kwargs)
        job.validate()

        get_backend().enqueue(job)
