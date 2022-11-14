import datetime
from abc import ABCMeta, abstractmethod
from typing import Tuple, TypeVar, Optional, Collection

from ..job import Job
from ..types import QueueName, WorkerNumber
from ..progress_logger import ProgressLogger, NULL_PROGRESS_LOGGER

# Work around https://github.com/python/mypy/issues/9914. Name needs to match
# that in progress_logger.py.
T = TypeVar('T')


class BaseBackend(metaclass=ABCMeta):
    def startup(self, queue: QueueName) -> None:
        pass

    @abstractmethod
    def enqueue(self, job: Job, queue: QueueName) -> None:
        raise NotImplementedError()

    def bulk_enqueue(self, jobs: Collection[Job], queue: QueueName) -> None:
        """
        Enqueue a number of tasks in one pass.

        The jobs will be inserted in the order provided in the given collection.

        Backends are strongly encouraged to override this with a more efficient
        implemenation if they can.
        """
        for job in jobs:
            self.enqueue(job, queue)

    @abstractmethod
    def dequeue(self, queue: QueueName, worker_num: WorkerNumber, timeout: int) -> Optional[Job]:
        raise NotImplementedError()

    @abstractmethod
    def length(self, queue: QueueName) -> int:
        raise NotImplementedError()

    def processed_job(self, queue: QueueName, worker_num: WorkerNumber, job: Job) -> None:
        pass


class BackendWithDeduplicate(BaseBackend, metaclass=ABCMeta):
    @abstractmethod
    def deduplicate(
        self,
        queue: QueueName,
        *,
        progress_logger: ProgressLogger = NULL_PROGRESS_LOGGER
    ) -> Tuple[int, int]:
        raise NotImplementedError()


class BackendWithClear(BaseBackend, metaclass=ABCMeta):
    @abstractmethod
    def clear(self, queue: QueueName) -> None:
        raise NotImplementedError()


class BackendWithPause(BaseBackend, metaclass=ABCMeta):
    @abstractmethod
    def pause(self, queue: QueueName, until: datetime.datetime) -> None:
        raise NotImplementedError()

    @abstractmethod
    def is_paused(self, queue: QueueName) -> bool:
        raise NotImplementedError()


class BackendWithPauseResume(BackendWithPause, metaclass=ABCMeta):
    @abstractmethod
    def resume(self, queue: QueueName) -> None:
        raise NotImplementedError()
