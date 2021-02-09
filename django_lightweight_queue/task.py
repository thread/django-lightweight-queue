from typing import Any, Generic, TypeVar, Callable, Optional

from . import app_settings
from .job import Job
from .types import QueueName
from .utils import get_backend, contribute_implied_queue_name

TCallable = TypeVar('TCallable', bound=Callable[..., Any])


class task:
    def __init__(
        self,
        queue: str = 'default',
        timeout: Optional[int] = None,
        sigkill_on_stop: bool = False,
        atomic: Optional[bool] = None,
    ) -> None:
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

            `atomic` -- The task will be run inside a database transaction.

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

        if atomic is None:
            atomic = app_settings.ATOMIC_JOBS

        self.queue = QueueName(queue)
        self.timeout = timeout
        self.sigkill_on_stop = sigkill_on_stop
        self.atomic = atomic

        contribute_implied_queue_name(self.queue)

    def __call__(self, fn: TCallable) -> 'TaskWrapper[TCallable]':
        return TaskWrapper(fn, self.queue, self.timeout, self.sigkill_on_stop, self.atomic)


class TaskWrapper(Generic[TCallable]):
    def __init__(
        self,
        fn: TCallable,
        queue: QueueName,
        timeout: Optional[int],
        sigkill_on_stop: bool,
        atomic: bool,
    ):
        self.fn = fn
        self.queue = queue
        self.timeout = timeout
        self.sigkill_on_stop = sigkill_on_stop
        self.atomic = atomic

        self.path = '{}.{}'.format(fn.__module__, fn.__name__)

    def __repr__(self) -> str:
        return "<TaskWrapper: {}>".format(self.path)

    def __call__(self, *args: Any, **kwargs: Any) -> None:
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

        get_backend(queue).enqueue(job, queue)
