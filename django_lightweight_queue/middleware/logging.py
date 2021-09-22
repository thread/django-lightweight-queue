import logging

from ..job import Job
from ..types import QueueName, WorkerNumber, SysExcInfoType

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    def process_job(self, job: Job, queue: QueueName, worker_num: WorkerNumber) -> None:
        logger.info("Running job {}".format(job))

    def process_result(self, job: Job, result: bool, duration: float) -> None:
        logger.info("Finished job => {!r} (Time taken: {:.2f}s)".format(
            result,
            duration,
        ))

    def process_exception(self, job: Job, duration: float, *exc_info: SysExcInfoType) -> None:
        logger.exception("Exception when processing job (duration: {:.2f}s)".format(
            duration,
        ))
