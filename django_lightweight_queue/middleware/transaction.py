from django.db import transaction

class TransactionMiddleware(object):
    def process_job(self, job):
        transaction.set_autocommit(False)

    def process_result(self, job, result, duration):
        transaction.commit()

    def process_exception(self, job, time_taken, *exc_info):
        transaction.rollback()
