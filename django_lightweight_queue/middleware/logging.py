import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    def process_job(self, job, queue, worker_num):
        logger.info("Running job {}".format(job))

    def process_result(self, job, result, duration):
        logger.info("Finished job => {!r} (Time taken: {:.2f}s)".format(
            result,
            duration,
        ))

    def process_exception(self, job, duration, *exc_info):
        logger.exception("Exception when processing job (duration: {:.2f}s)".format(
            duration,
        ))
