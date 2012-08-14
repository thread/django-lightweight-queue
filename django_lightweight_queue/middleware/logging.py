from __future__ import absolute_import

import logging
import traceback

log = logging.getLogger(__name__)

class LoggingMiddleware(object):
    def process_job(self, job):
        log.info("Running job %s", job)

    def process_result(self, job, result, duration):
        log.info("Finished job %s => %r (Time taken: %.2fs)",
            job,
            result,
            duration,
        )

    def process_exception(self, job, duration, *exc_info):
        log.error("Exception when processing %r (duration: %.2fs): %s",
            job,
            duration,
            ''.join(traceback.format_exception(*exc_info)),
        )
