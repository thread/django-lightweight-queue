from .job import Job
from .utils import get_backend

from . import app_settings

class task(object):
    def __init__(self, queue='default', timeout=None, sigkill_on_stop=False):
        """
        Define a task to be run.

            @task()
            def fn(arg1, arg2):
                # <do something with arg1, arg2, etc.>

            >>> fn("hello", 1)

        Note that arguments must be JSON serialisable and, therefore, cannot be
        Django model instances. This is entirely deliberate due to:

            a) Transparency when inspecting the queue

            b) Avoiding state/caching/etc issues on this kinds of instances
               generally.

        You can set some default options on `@task()`s:

            `queue` -- Which queue to run the task in. You can invent queue
            names; the worker's will be created automatically.

            `timeout` -- The task will be SIGKILL'd after it has run for *at
            least* this many seconds. Note that in most circumstances you want
            `sigkill_on_stop` (below) instead.

            `sigkill_on_stop` -- The task will be SIGKILL'd when the queue
            processor is shut down. The default behaviour is to let it run to
            completion.

        For example::

            @task(sigkill_on_stop=True, timeout=60)
            def slow_fn(arg):
                time.sleep(600)

            >>> slow_fn(1)

        You can also dynamically override values at call time if you provide a
        `django_lightweight_queue_` prefix::

            @task(sigkill_on_stop=True, timeout=60)
            def slow_fn(arg):
                time.sleep(600)

            >>> slow_fn(2, django_lightweight_queue_timeout=30)

        (NB. You cannot yet invent dynamic queue names here; a queue with that
        name must already be running.)
        """

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
        # Allow us to override the default values dynamically
        timeout = kwargs.pop('django_lightweight_queue_timeout', self.timeout)
        sigkill_on_stop = kwargs.pop(
            'django_lightweight_queue_sigkill_on_stop',
            self.sigkill_on_stop,
        )

        # Allow queue overrides, but you must ensure that this queue will exist
        queue = kwargs.pop('django_lightweight_queue_queue', self.queue)

        job = Job(self.path, args, kwargs, timeout, sigkill_on_stop)
        job.validate()

        get_backend().enqueue(job, queue)
