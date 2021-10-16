import sys
import json
import time
import datetime
import warnings
from typing import Any, Dict, Tuple, Callable, Optional, TYPE_CHECKING

from django.db import transaction

from .types import QueueName, WorkerNumber
from .utils import get_path, get_middleware

if TYPE_CHECKING:
    from .task import TaskWrapper

TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


class Job:
    def __init__(
        self,
        path: str,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        timeout: Optional[int] = None,
        sigkill_on_stop: bool = False,
    ) -> None:
        self.path = path
        self.args = args
        self.kwargs = kwargs
        self.timeout = timeout
        self.sigkill_on_stop = sigkill_on_stop
        self.created_time = datetime.datetime.utcnow()

        self._json = None  # type: Optional[str]

    def __repr__(self) -> str:
        return "<Job: {}(*{!r}, **{!r}) @ {}>".format(
            self.path,
            self.args,
            self.kwargs,
            self.created_time_str,
        )

    @classmethod
    def from_json(cls, val: str) -> 'Job':
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
    def created_time_str(self) -> str:
        return self.created_time.strftime(TIME_FORMAT)

    def run(self, *, queue: QueueName, worker_num: WorkerNumber) -> bool:
        """
        `queue` and `worker_num` arguments are required for context only and do
        not change the behaviour of job execution.
        """

        start = time.time()

        middleware = get_middleware()

        for instance in middleware:
            if hasattr(instance, 'process_job'):
                instance.process_job(self, queue, worker_num)

        try:
            task = self.get_task_instance()

            if task.atomic:
                with transaction.atomic():
                    result = task.fn(*self.args, **self.kwargs)
            else:
                result = task.fn(*self.args, **self.kwargs)

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

    def validate(self) -> None:
        # Ensure these execute without exception so that we cannot enqueue
        # things that are impossible to dequeue.
        self.get_task_instance()
        self.to_json()

    def get_task_instance(self) -> 'TaskWrapper[Callable[..., Any]]':
        return get_path(self.path)

    def get_fn(self) -> 'TaskWrapper[Callable[..., Any]]':
        warnings.warn(
            "Job.get_fn is deprecated, call Job.get_task_instance instead.",
            DeprecationWarning,
        )
        return self.get_task_instance()

    def as_dict(self) -> Dict[str, Any]:
        return {
            'path': self.path,
            'args': self.args,
            'kwargs': self.kwargs,
            'timeout': self.timeout,
            'sigkill_on_stop': self.sigkill_on_stop,
            'created_time': self.created_time_str,
        }

    def to_json(self) -> str:
        if self._json is None:
            self._json = json.dumps(self.as_dict())
        return self._json

    def identity_without_created(self) -> str:
        """Returns an object which can be used to identify equivalent jobs"""
        self_dict = self.as_dict()
        del self_dict['created_time']
        return json.dumps(self_dict, sort_keys=True)
