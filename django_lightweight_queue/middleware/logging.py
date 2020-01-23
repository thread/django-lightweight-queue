import json
import logging
import traceback

log = logging.getLogger(__name__)

class LoggingMiddleware(object):
    def process_job(self, job):
        log.info("Running job %s", job)

        self.fluent_log(job, state='processing')

    def process_result(self, job, result, duration):
        log.info("Finished job => %r (Time taken: %.2fs)",
            result,
            duration,
        )

        self.fluent_log(job, state='finished', duration=duration)

    def process_exception(self, job, duration, *exc_info):
        exception = ''.join(traceback.format_exception(*exc_info))

        log.error("Exception when processing job (duration: %.2fs): %s",
            duration,
            exception,
        )

        self.fluent_log(
            job,
            state='exception',
            duration=duration,
            exception=exception,
        )

    def fluent_log(self, job, **kwargs):
        data = job.as_dict()

        data.update(kwargs)

        data['fluent_log'] = True

        log.info(json.dumps(data))
