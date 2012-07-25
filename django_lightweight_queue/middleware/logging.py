import traceback

class LoggingMiddleware(object):
    def process_job(self, job):
        print "I: Running job %s(*%r, **%r)" % (
            job.path,
            job.args,
            job.kwargs,
        )

    def process_result(self, job, result, duration):
        print "I: Finished job %s(*%r, **%r) => %r (Time taken: %.2fs)" % (
            job.path,
            job.args,
            job.kwargs,
            result,
            duration,
        )

    def process_exception(self, job, time_taken, *exc_info):
        traceback.print_exception(*exc_info)
