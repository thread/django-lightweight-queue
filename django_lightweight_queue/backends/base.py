from abc import ABCMeta, abstractmethod

from ..job import Job


class BaseBackend(metaclass=ABCMeta):
    def startup(self, queue: str) -> None:
        pass

    @abstractmethod
    def enqueue(self, job: Job, queue: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def dequeue(self, queue: str, worker_num: int, timeout: float) -> Job:
        raise NotImplementedError()

    @abstractmethod
    def length(self, queue: str) -> int:
        raise NotImplementedError()

    def processed_job(self, queue: str, worker_num: int, job: Job) -> None:
        pass
