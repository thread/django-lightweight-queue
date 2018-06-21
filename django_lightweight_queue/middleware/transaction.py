from django.db import transaction

class TransactionMiddleware(object):
    def process_job(self, job):
        transaction.atomic().__enter__()

    def process_result(self, job, result, duration):
        transaction.atomic().__exit__(None, None, None)

    def process_exception(self, job, time_taken, *exc_info):
        transaction.atomic().__exit__(*exc_info)
