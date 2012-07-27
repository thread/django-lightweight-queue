import traceback

from django.db import transaction

class TransactionMiddleware(object):
    def process_job(self, job):
        transaction.enter_transaction_management()
        transaction.managed(True)

    def process_result(self, job, result, duration):
        if transaction.is_managed():
            if transaction.is_dirty():
                transaction.commit()
            transaction.leave_transaction_management()

    def process_exception(self, job, time_taken, *exc_info):
        if transaction.is_dirty():
            transaction.rollback()
        transaction.leave_transaction_management()
