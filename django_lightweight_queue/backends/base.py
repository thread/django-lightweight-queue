from abc import ABCMeta, abstractmethod
from typing import Optional

from ..job import Job
from ..types import QueueName


class BaseBackend(metaclass=ABCMeta):
    def startup(self, queue: QueueName) -> None:
        pass

    @abstractmethod
    def enqueue(self, job: Job, queue: QueueName) -> None:
        raise NotImplementedError()

    @abstractmethod
    def dequeue(self, queue: QueueName, worker_num: int, timeout: float) -> Optional[Job]:
        raise NotImplementedError()

    @abstractmethod
    def length(self, queue: QueueName) -> int:
        raise NotImplementedError()

    def processed_job(self, queue: QueueName, worker_num: int, job: Job) -> None:
        pass
