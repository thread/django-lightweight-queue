import traceback

class LoggingMiddleware(object):
    def process_job(self, job):
        print "I: Running job %s" % job

    def process_result(self, job, result, duration):
        print "I: Finished job %s => %r (Time taken: %.2fs)" % (
            job,
            result,
            duration,
        )

    def process_exception(self, job, time_taken, *exc_info):
        traceback.print_exception(*exc_info)
