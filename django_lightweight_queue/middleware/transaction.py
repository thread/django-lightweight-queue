from django.db import transaction, connection

class TransactionMiddleware(object):
    def process_job(self, job):
        if not connection.in_atomic_block:
            transaction.set_autocommit(False)

    def process_result(self, job, result, duration):
        if not connection.in_atomic_block:
            transaction.commit()

    def process_exception(self, job, time_taken, *exc_info):
        if not connection.in_atomic_block:
            transaction.rollback()
